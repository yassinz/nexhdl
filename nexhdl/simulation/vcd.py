"""VCD tracing with support for complex types (arrays, structs)."""

from circt.dialects import hw
from .states import get_storage_layout, get_bitwidth

class VCDTracer:
    """
    VCD waveform tracer with complex type support.
    
    Flattens arrays and structs into hierarchical signals while respecting
    the physical memory layout (padding, alignment) of the simulator.
    """
    
    def __init__(self, simulator, filename="trace.vcd", timescale='1ns'):
        self.simulator = simulator
        self.filename = filename
        self.timescale = timescale
        self.file = None
        self.signals = []  # List of {abbrev, name, byte_offset, numbits, storage_bytes, previous}
        self.time = 0
        self.tracing = False
        self._abbrev_counter = 0
    
    def _next_abbrev(self) -> str:
        """Generate next signal abbreviation."""
        self._abbrev_counter += 1
        abbrev = ''
        rest = self._abbrev_counter
        while rest != 0:
            c = (rest % 84) + 33
            if c >= ord('0'):
                c += 10
            abbrev += chr(c)
            rest //= 84
        return abbrev
    
    def _add_to_scope_tree(self, tree, name_parts, circt_type, byte_offset):
        """Recursively build a scope tree from path parts and CIRCT types.
        
        Args:
            tree: The scope tree being built
            name_parts: Path components (e.g., ['module', 'reg'])
            circt_type: CIRCT type of the signal
            byte_offset: Offset in BYTES from start of buffer
        """
        # 1. Handle Hierarchy (recurse down names)
        if len(name_parts) > 1:
            sub = name_parts[0]
            if sub not in tree:
                tree[sub] = {}
            if not isinstance(tree[sub], dict):
                # Conflict: name used as both scope and leaf. Move leaf.
                tree[sub + "_val"] = tree[sub]
                tree[sub] = {}
            self._add_to_scope_tree(tree[sub], name_parts[1:], circt_type, byte_offset)
            return

        name = name_parts[0]

        # 2. Handle Complex Types (Flattening)
        if hw.ArrayType.isinstance(circt_type):
            arr_type = hw.ArrayType(circt_type)
            elem_type = arr_type.element_type
            
            # Determine stride based on storage layout
            elem_size_bytes, _ = get_storage_layout(elem_type)
            
            if name not in tree or not isinstance(tree[name], dict):
                tree[name] = {}
                
            for i in range(arr_type.size):
                # Array index 0 is at Lowest Address
                next_offset = byte_offset + (i * elem_size_bytes)
                self._add_to_scope_tree(tree[name], [f"[{i}]"], elem_type, next_offset)

        elif hw.StructType.isinstance(circt_type):
            struct_type = hw.StructType(circt_type)
            
            if name not in tree or not isinstance(tree[name], dict):
                tree[name] = {}
            
            # struct fields need specific offset calculation matching serialization:
            # 1. Iterate REVERSE to calculate physical offsets (MSB-first packing)
            # 2. Store offsets in map
            field_offsets = {}
            current_off = byte_offset
            
            # Calculate Offsets (Logic matches serialization.py)
            for f_name, f_type in reversed(struct_type.get_fields()):
                f_size, f_align = get_storage_layout(f_type)
                
                # Apply Alignment Padding
                padding = (f_align - (current_off % f_align)) % f_align
                current_off += padding
                
                field_offsets[f_name] = current_off
                current_off += f_size
                
            # Add to Tree (In definition order for standard VCD viewing)
            for f_name, f_type in struct_type.get_fields():
                self._add_to_scope_tree(tree[name], [f_name], f_type, field_offsets[f_name])

        else:
            # 3. Handle Leaf Types (Integer / Clock)
            storage_bytes, _ = get_storage_layout(circt_type)
            
            # Store tuple: (Type, ByteOffset, StorageBytes)
            val_entry = (circt_type, byte_offset, storage_bytes)
            
            if name in tree and isinstance(tree[name], dict):
                tree[name + "_val"] = val_entry
            else:
                tree[name] = val_entry

    def _write_scope_tree(self, tree, depth):
        """Traverse the scope tree and write VCD header blocks."""
        indent = "    " * depth
        for name in sorted(tree.keys()):
            val = tree[name]
            
            if isinstance(val, dict):
                # It's a scope (Module, Struct, or Array container)
                self.file.write(f"{indent}$scope module {name} $end\n")
                self._write_scope_tree(val, depth + 1)
                self.file.write(f"{indent}$upscope $end\n")
            else:
                # It's a leaf signal
                circt_type, byte_offset, storage_bytes = val
                
                numbits = get_bitwidth(circt_type)
                abbrev = self._next_abbrev()
                var_type = 'wire'
                
                self.file.write(f"{indent}$var {var_type} {numbits} {abbrev} {name}")
                if numbits > 1:
                    self.file.write(f" [{numbits-1}:0]")
                self.file.write(" $end\n")
                
                self.signals.append({
                    'abbrev': abbrev, 
                    'name': name,
                    'byte_offset': byte_offset, 
                    'numbits': numbits, 
                    'storage_bytes': storage_bytes,
                    'previous': None
                })

    def writeHeader(self):
        """Write VCD header with hierarchical signals."""
        self.file.write("$date\n    Generated by NexHDL Simulator\n$end\n")
        self.file.write("$version\n    NexHDL/CIRCT Arcilator\n$end\n")
        self.file.write(f"$timescale {self.timescale} $end\n")
        
        # Build the signal tree
        root = {self.simulator.name: {}}
        top_scope = root[self.simulator.name]
        
        # 1. Register ports
        for port_name, port in self.simulator.states_info.ports.items():
            self._add_to_scope_tree(top_scope, port.name.split('/'), port.type, port.offset)
        
        # 2. Register internal states
        for state in self.simulator.states_info.unique_states:
            for name in state.names:
                self._add_to_scope_tree(top_scope, name.split('/'), state.type, state.offset)
        
        # Write the tree to file
        self._write_scope_tree(root, depth=0)
        self.file.write("$enddefinitions $end\n")
    
    def writeDumpvars(self):
        """Write initial values."""
        self.file.write("$dumpvars\n")
        self._writeValues(include_unchanged=True)
    
    def _readSignalValue(self, signal) -> int:
        """
        Read a single signal's integer value from buffer using physical storage size.
        """
        byte_offset = signal['byte_offset']
        storage_bytes = signal['storage_bytes']
        
        # Bounds check
        if byte_offset + storage_bytes > len(self.simulator.buffer):
            return 0
            
        data = self.simulator.buffer[byte_offset : byte_offset + storage_bytes]
        return int.from_bytes(data, byteorder='little', signed=False)
    
    def _writeValues(self, include_unchanged=False):
        """Write current signal values."""
        for signal in self.signals:
            value = self._readSignalValue(signal)
            
            if not include_unchanged and value == signal['previous']:
                continue
            
            numbits = signal['numbits']
            if numbits > 1:
                self.file.write('b')
                # Format as binary string
                bin_str = format(value, f'0{numbits}b')
                # If value exceeds numbits (due to storage padding), truncate
                if len(bin_str) > numbits:
                    bin_str = bin_str[-numbits:]
                self.file.write(bin_str)
                self.file.write(' ')
            else:
                self.file.write('1' if value & 1 else '0')
            
            self.file.write(f"{signal['abbrev']}\n")
            signal['previous'] = value
    
    def writeTimestep(self, increment=1):
        """Write timestep and changed values."""
        self.time += increment
        self.file.write(f"#{self.time}\n")
        self._writeValues()
    
    def start(self):
        """Start VCD tracing."""
        self.file = open(self.filename, 'w')
        self.time = 0
        self._abbrev_counter = 0
        self.signals = []
        self.tracing = True
        self.writeHeader()
        self.writeDumpvars()
    
    def stop(self):
        """Stop VCD tracing."""
        if self.tracing:
            self.tracing = False
            if self.file:
                self.file.close()
            self.file = None
            self.signals = []
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()