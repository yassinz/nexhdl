"""
Module - Base class for hardware modules
"""

from circt.dialects import hw
from circt.passmanager import PassManager
import circt
import io

from ..types.base import to_nex_type, NexType
from ..simulation import Simulator
from .meta import ModuleMeta
from .hwmodule import HWModule
from .trace import TraceVars
from .io import IO
from .context import (
    CompilationContextManager, 
    get_current_context, 
    CompilationContext, 
    ScopeContext
)


class Module(metaclass=ModuleMeta):
    """
    Base class for hardware modules.
    
    Define modules by subclassing and adding port annotations:
    
        class Adder(Module):
            a: INPUT[Logic[32]]
            b: INPUT[Logic[32]]
            out: OUTPUT[Logic[32]]
            
            def build(self, io):
                io.out = io.a + io.b
    """
    
    def __init__(self):
        """Initialize module."""
        self.is_compiled = False
        self.hw_module = None
        self.model = None
        self._context = None
    
    def compile(self, context=None):
        """Compile the module to CIRCT IR."""
        if self.is_compiled:
            return
        
        try:
            # Check if we're compiling within another module
            is_nested = context is not None
            
            if is_nested:
                # Nested compilation - reuse existing context
                # Unwrap potentially nested scopes to get the true global context
                global_ctx = getattr(context, 'global_context', context)
                self._context = ScopeContext(global_ctx)
                
                self.model = context.model
                if self.name in context.instances:
                    self.hw_module = context.instances[self.name]
                    self.is_compiled = True
                    return
                insertion_point = circt.ir.InsertionPoint.at_block_begin(self.model.body)
            else:
                # Top-level compilation - create new context
                global_ctx = CompilationContext()
                self._context = ScopeContext(global_ctx)
                
                self.model = circt.ir.Module.create()
                self._context.model = self.model
                insertion_point = circt.ir.InsertionPoint(self.model.body)
            
            with insertion_point:
                # Create HW module
                ports = [(name, direction, NexType.to_circt(self._port_type_objs[name])) 
                         for name, direction in self.ports]
                
                has_build = hasattr(self, 'build')
                self.hw_module = HWModule(self.name, ports, is_nested, external=not has_build)
                
                if is_nested:
                    self._context.instances[self.name] = self.hw_module
                
                # Build module body if build method exists
                if has_build:
                    self._build_body()
            
            self.is_compiled = True
            
            # Clean up if top-level
            if not is_nested:
                self.model.operation.verify()
                
        except Exception as e:
            self.is_compiled = False
            raise e
    
    def _build_body(self):
        """Build the module body with proper error handling."""
        # Create IO interface
        io_inputs = []
        for name, arg in zip(self.hw_module.input_names, self.hw_module.arguments):
            type_obj = self._port_type_objs[name]
            nex_type = to_nex_type(type_obj)
            io_inputs.append((name, nex_type(arg)))
        
        io_outputs = [(name, to_nex_type(self._port_type_objs[name])) 
                      for name, _ in self.outputs]
        interfaces = getattr(self, '_interfaces', {})
        io = IO(self.name, io_inputs, io_outputs, self.inouts, interfaces=interfaces)
        
        # Build with proper insertion point and tracing
        # Pass context to nested module instantiations
        insertion_point = circt.ir.InsertionPoint(self.hw_module.entry_block)
        with insertion_point, CompilationContextManager(self._context):
            # Run build with TraceVars to capture names
            with TraceVars():
                self.build(io)
            
            io.check_complete()
            
            # Verify primitives
            for reg in self._context.regs:
                if not reg._reg_is_wired:
                    name = getattr(reg, '_nex_name', None) or 'unnamed'
                    raise RuntimeError(
                        f"Reg '{name}' inside module '{self.name}' was created but never assigned. "
                        f"Use '{name}.next = ...' to assign a value."
                    )
            
            for wire in self._context.wires:
                if not wire._wire_is_assigned:
                    name = getattr(wire, '_nex_name', None) or 'unnamed'
                    raise RuntimeError(
                        f"Wire '{name}' inside module '{self.name}' was created but never assigned. "
                        f"Use '{name}.assign = ...' to assign a value."
                    )
            
            # Generate output
            results = [io.outputs[name].value for name, _ in self.outputs]
            if results:
                hw.output(results)
    
    @property
    def module(self):
        """Return the compiled module."""
        if not self.is_compiled:
            self.compile()
        return self.model
    
    def verilog(self, passes=None, debug=False):
        """Generate Verilog from the compiled module."""
        if passes is None:
            passes = [
                "builtin.module(lower-esi-to-physical, lower-esi-ports, lower-esi-to-hw)",
                "builtin.module(hw.module(lower-seq-fifo))",
                "builtin.module(hw.module(lower-seq-hlmem))",
                "builtin.module(lower-seq-to-sv)",
                #"builtin.module(hw-flatten-modules)",
                "builtin.module(hw.module(hw-cleanup{merge-always-blocks}))",
                "builtin.module(cse, canonicalize)",
            ]

        m = circt.ir.Module.parse(str(self.module))
        for ps in passes:
            PassManager.parse(ps).run(m.operation)

        buffer = io.StringIO()
        circt.export_verilog(m, buffer)
        verilog = buffer.getvalue()

        # Remove comments
        if not debug:
            verilog = verilog.splitlines()
            verilog = '\n'.join([v.split("//")[0] for v in verilog])
        
        return verilog
    
    def simulate(self):
        """Create a simulator for the module."""
        return Simulator(self.module, self.name)
    
    def mlir(self):
        """Return the MLIR representation."""
        return str(self.module)
    
    def __repr__(self):
        return f"<Module {self.name}>"
