"""
Simulator
"""

import circt
import io
import ctypes
from sys import byteorder
import llvmlite.binding as llvmite

from .transforms import translate_to_llvm
from .vcd import VCDTracer
from .states import read_value, write_value



class PortDescriptor:
    """
    Descriptor for IO port access.
    Usage: sim.io.port_name
    """
    def __init__(self, data, buffer):
        self.data = data # PortData
        self.buffer = buffer

    def __get__(self, instance, owner):
        return read_value(self.buffer, self.data.offset, self.data.type)

    def __set__(self, instance, value):
        if self.data.direction == 'output':
            raise AttributeError(f"Cannot write to output port '{self.data.name}'")
        write_value(self.buffer, self.data.offset, value, self.data.type, name=self.data.name)


class MemoryView:
    """
    View for hardware memory that wraps a Python built-in memoryview.
    Supports slicing, casting, and standard buffer protocols.
    """
    def __init__(self, data, buffer):
        self.data = data # MemoryData
        self.buffer = buffer
        
        # 1. Create a raw memoryview of the specific slice of the simulator buffer
        start = data.offset
        stride_bytes = data.stride
        end = start + (data.depth * stride_bytes)
        
        self._raw_view = memoryview(buffer)[start:end]
        
        # 2. Try to cast to a typed view if the bit-width matches standard C types
        # This makes operations like self[i] significantly faster.
        self._typed_view = self._try_cast(data.word_numbits, data.stride)

    def _try_cast(self, bits, stride_bytes):
        """Maps hardware bit-widths to Python memoryview format characters."""
        # Map bits to format: B=u8, H=u16, I=u32, Q=u64
        # We only cast if the stride matches the natural alignment
        mapping = {8: 'B', 16: 'H', 32: 'I', 64: 'Q'}
        
        fmt = mapping.get(bits)
        if not fmt:
            return None
            
        # Verify if stride matches type size (e.g., don't cast 32-bit if stride is 8 bytes)
        # stride is in BYTES. sizeof is in BYTES.
        type_size_bytes = ctypes.sizeof(getattr(ctypes, f"c_uint{bits}"))
        if type_size_bytes == stride_bytes:
            try:
                # Cast to 1D array of the specific type
                return self._raw_view.cast(fmt, shape=(self.data.depth,))
            except (ValueError, TypeError):
                return None
        return None

    def _get_addr(self, index):
        if index < 0:
            index += self.data.depth
        if index < 0 or index >= self.data.depth:
            raise IndexError(f"Memory index {index} out of range (depth {self.data.depth})")
        return self.data.offset + (index * self.data.stride)

    def __getitem__(self, index):
        # Use high-performance typed view if available
        if self._typed_view is not None:
            return self._typed_view[index]
        
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self.data.depth))]

        if not isinstance(index, int):
             raise TypeError(f"Memory index must be int or slice, got {type(index).__name__}")
        
        return read_value(self.buffer, self._get_addr(index), self.data.word_type)

    def __setitem__(self, index, value):
        if self._typed_view is not None:
            self._typed_view[index] = value
            return

        if isinstance(index, slice):
            indices = range(*index.indices(self.data.depth))
            
            # Handle Sequence assignment (must match length)
            if isinstance(value, (list, tuple, memoryview)):
                if len(value) != len(indices):
                    raise ValueError(f"Could not assign sequence of size {len(value)} to slice of size {len(indices)}")
                for i, v in zip(indices, value):
                    self[i] = v
            # Handle Scalar broadcasting
            else:
                for i in indices:
                    self[i] = value
            return

        if not isinstance(index, int):
             raise TypeError(f"Memory index must be int or slice, got {type(index).__name__}")
        
        # We can construct a precise name for the element being written
        element_name = f"{self.data.name}[{index}]"
        write_value(self.buffer, self._get_addr(index), value, self.data.word_type, name=element_name)

    def __len__(self):
        return self.data.depth
    
    def __iter__(self):
        if self._typed_view is not None:
            yield from self._typed_view
        else:
            for i in range(self.data.depth):
                yield self[i]

    def __enter__(self):
        return self._typed_view if self._typed_view is not None else self._raw_view

    def __exit__(self, *args):
        pass

    def tobytes(self):
        return self._raw_view.tobytes()

    def cast(self, format, shape=None):
        """Expose the built-in cast functionality."""
        return self._raw_view.cast(format, shape)

    def __repr__(self):
        # Show a preview (first 8 elements)
        limit = 8
        items = [repr(self[i]) for i in range(min(self.data.depth, limit))]
        if self.data.depth > limit:
            items.append("...")
        return f"[{', '.join(items)}]"


class IO:
    """
    IO interface container for dynamic port access.
    """
    def __init__(self, ports_data, buffer, module_name):
        self._ports = ports_data # dict name -> PortData
        self._buffer = buffer
        self.module_name = module_name
        
        # Create descriptors for each port
        attrs = {}
        for name, data in ports_data.items():
            attrs[name] = PortDescriptor(data, buffer)
        
        # Add __setattr__ to catch writes to non-existent ports
        def io_setattr(self, name, value):
            if name.startswith('_') or name == 'module_name':
                object.__setattr__(self, name, value)
            elif name not in self._ports:
                raise AttributeError(f"Port '{name}' not found in module '{self.module_name}'")
            else:
                # Let the descriptor handle it
                object.__setattr__(self, name, value)
        
        attrs['__setattr__'] = io_setattr
            
        # Dynamically create a class for this instance to hold descriptors
        self.__class__ = type(f'{module_name}_IO', (IO,), attrs)
        
    @property
    def buffer(self):
        return self._buffer

    @property
    def outputs(self):
        return {name: data for name, data in self._ports.items() if data.direction == 'output'}
    
    @property
    def inputs(self):
         return {name: data for name, data in self._ports.items() if data.direction == 'input'}

    @property
    def clocks(self):
        return {name: data for name, data in self._ports.items() if str(data.type) == "!seq.clock"}

    def __repr__(self):
        inputs = [name for name, data in self._ports.items() if data.direction == 'input']
        outputs = [name for name, data in self._ports.items() if data.direction == 'output']
        return f"<{self.module_name}_IO inputs={inputs} outputs={outputs}>"

    # Allow cleaner introspection
    def __dir__(self):
        return list(self._ports.keys()) + super().__dir__()


class States:
    """
    Container for internal states.
    Usage: sim.states['module/reg']
    """
    def __init__(self, states_info, buffer):
        self._states_info = states_info # StatesInfo
        self._buffer = buffer

    def __getitem__(self, key):
        if key not in self._states_info.states:
             raise KeyError(f"State '{key}' not found")
        data = self._states_info.states[key]
        return read_value(self._buffer, data.offset, data.type)

    def __setitem__(self, key, value):
        if key not in self._states_info.states:
             raise KeyError(f"State '{key}' not found")
        data = self._states_info.states[key]
        write_value(self._buffer, data.offset, value, data.type, name=key)
    
    def keys(self):
        return self._states_info.states.keys()

    def __repr__(self):
        # Show all names associated with each unique state
        items = [f"[{', '.join(s.names)}]" for s in self._states_info.unique_states]
        return f"<States count={len(self._states_info.unique_states)} items={items}>"


class Memories:
    """
    Container for memories.
    Usage: sim.memories['ram'] -> MemoryView
    """
    def __init__(self, memories_data, buffer):
        self._memories_data = memories_data # dict name -> MemoryData
        self._buffer = buffer
        self._views = {} # cache

    def __getitem__(self, key):
        if key not in self._memories_data:
            short_key = [k for k in self._memories_data.keys() if k.endswith(key + '_ext')]
            if not short_key:
                raise KeyError(f"Memory '{key}' not found")
            key = short_key[0]
            
        if key not in self._views:
            self._views[key] = MemoryView(self._memories_data[key], self._buffer)
        return self._views[key]
        
    def keys(self):
        return self._memories_data.keys()

    def __repr__(self):
        params = [f"{name}: {data.depth}x{data.word_numbits}" for name, data in self._memories_data.items()]
        return f"<Memories count={len(self._memories_data)} items={params}>"


class Simulator:
    """
    Hardware simulator.
    """
    
    def __init__(self, model: circt.ir.Module, name: str):
        self.model = model
        self.name = name
        
        # Lower to LLVM through Arc dialect
        self.module_mlir_arc, self.states_info = translate_to_llvm(self.model)
        
        # Allocate state storage (size calculated in states_info)
        self.buffer = (ctypes.c_ubyte * self.states_info.size)()
        
        # Initialize Containers
        self.io = IO(self.states_info.ports, self.buffer, self.name)
        self.states = States(self.states_info, self.buffer)
        self.memories = Memories(self.states_info.memories, self.buffer)
        
        # Compile to machine code
        self.module_llvm_ir = self._module_to_llvmir(self.module_mlir_arc)
        self._init_engine()
        self.func = self._get_function(f"{self.name}_eval")
        self.run_func = self._get_function(f"{self.name}_run", [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64])
        
        self.tracer = None

    def _module_to_llvmir(self, module: circt.ir.Module) -> str:
        """Export CIRCT module to LLVM IR string with an optimized run loop."""
        buffer = io.StringIO()
        circt.export_llvm_ir(module, buffer)
        ir = buffer.getvalue().replace("nocreateundeforpoison", "")
        ir = ir.replace("captures(none)", "nocapture")

        # Injected high-performance run loop
        ir += f"""
            define void @{self.name}_run(ptr %0, i64 %1, i64 %2) {{
                entry:
                    %p = getelementptr i8, ptr %0, i64 %1
                    store i8 0, ptr %p, align 1
                    %z = icmp eq i64 %2, 0
                    br i1 %z, label %exit, label %loop
                exit:
                    ret void
                loop:
                    %i = phi i64 [ %ni, %loop ], [ 0, %entry ]
                    store i8 1, ptr %p, align 1
                    tail call void @{self.name}_eval(ptr %0)
                    store i8 0, ptr %p, align 1
                    tail call void @{self.name}_eval(ptr %0)
                    %ni = add i64 %i, 1
                    %d = icmp eq i64 %ni, %2
                    br i1 %d, label %exit, label %loop
            }}
        """
        return ir

    def _get_function(self, name, argtypes=[ctypes.c_void_p]):
        """Get compiled function pointer"""
        func_ptr = self.engine.get_function_address(name)
        if not func_ptr:
            raise Exception(f"Function '{name}' not found in the compiled module")
        return ctypes.CFUNCTYPE(None, *argtypes)(func_ptr)
    
    def vcd(self, filename="trace.vcd", timescale='1ns'):
        """Start VCD tracing."""
        self.tracer = VCDTracer(self, filename, timescale)
        self.tracer.start()
        return self.tracer
        
    def step(self):
        """Execute one simulation step"""
        self.func(self.buffer)
        if self.tracer and self.tracer.tracing:
            self.tracer.writeTimestep()
    
    def _get_clk(self, name):
        """Find clock port by name or auto-detect."""
        if name: return name
        clks = [n for n, p in self.states_info.inputs.items() if str(p.type) == "!seq.clock"]
        if not clks: raise Exception(f"No clock ports found in '{self.name}' module, Use 'step' method for non-clock modules")
        return clks[0]

    def tick(self, clk_name=None):
        """Execute one clock cycle (falling + rising edge)"""
        clk = self._get_clk(clk_name)
        for val in [0, 1]:
            setattr(self.io, clk, val)
            self.step()

    def run(self, n, clk_name=None):
        """Execute N clock cycles efficiently"""
        if n <= 0: return
        clk_idx = self.states_info.ports[self._get_clk(clk_name)].offset
        self.run_func(self.buffer, clk_idx, n)
        if self.tracer and self.tracer.tracing:
            self.tracer.time += (n * 2) - 1
            self.tracer.writeTimestep()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.tracer:
            self.tracer.stop()
        self.engine.close()

    def llvm_ir(self):
        """Get LLVM IR string"""
        return str(self.module_llvm_ir)
    
    def mlir(self):
        """Get Arc MLIR string"""
        return str(self.module_mlir_arc)
    
    def machine_asm(self) -> str:
        """Get assembly code"""
        return self.target_machine.emit_assembly(self.compiled_module)
    
    def get_object(self) -> bytes:
        """Get object code"""
        return self.target_machine.emit_object(self.compiled_module)

    def _init_engine(self):
        """Initialize LLVM JIT engine"""
        llvmite.initialize_native_target()
        llvmite.initialize_native_asmprinter()
        llvmite.set_option("intel", "--x86-asm-syntax=intel")
        
        self.target = llvmite.Target.from_default_triple()
        self.target_machine = self.target.create_target_machine(opt=3)
        self.compiled_module = llvmite.parse_assembly(self.module_llvm_ir)
        self.compiled_module.verify()
        self.engine = llvmite.create_mcjit_compiler(self.compiled_module, self.target_machine)
        self.engine.finalize_object()
        self.engine.run_static_constructors()
