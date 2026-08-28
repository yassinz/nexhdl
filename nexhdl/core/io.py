"""
IO - Port interface for modules

Provides controlled access to module ports with validation.
"""

from nexhdl.types.base import NexValue

class IO:
    """
    Port interface for module build methods.
    
    Enforces port access rules:
    - Inputs: read-only
    - Outputs: write-once, read after assignment
    - Inouts: read-write
    """
    
    __slots__ = ('_module_name', '_ports', '_types', '_assigned', '_all_names', '_interfaces', '_interface_handles')
    
    def __init__(self, module_name, inputs, outputs, inouts, interfaces=None):
        """
        Initialize IO interface.
        
        Args:
            module_name: Name of the module (for error messages)
            inputs: List of (name, value) tuples
            outputs: List of (name, type_obj) tuples
            inouts: List of (name, value) tuples
            interfaces: Optional dict of {interface_name: InterfacePort}
        """
        self._module_name = module_name
        self._interfaces = interfaces or {}
        self._interface_handles = {}
        self._ports = {
            **{name: ('input', val) for name, val in inputs},
            **{name: ('output', None) for name, _ in outputs},
            **{name: ('inout', val) for name, val in inouts}
        }
        self._types = {name: type_obj for name, type_obj in outputs}
        self._assigned = {name for name, _ in outputs}  # Set of unassigned outputs
        self._all_names = tuple(self._ports.keys()) + tuple(self._interfaces.keys())  # Cache for error messages
    
    def __getattr__(self, name):
        """Get port value or interface handle."""
        if name in self._interfaces:
            if name not in self._interface_handles:
                spec = self._interfaces[name]
                self._interface_handles[name] = spec.interface_cls.create_handle(name, spec, self)
            return self._interface_handles[name]

        port = self._ports.get(name)
        if port is None:
            raise AttributeError(self._error_no_port(name))
        
        port_type, value = port
        
        # Check if output is assigned
        if port_type == 'output' and name in self._assigned:
            raise AttributeError(
                f"Cannot read output port '{name}' before assignment in module '{self._module_name}'.\n"
                f"Hint: Assign a value first with: io.{name} = <value>"
            )
        
        return value
    
    def __setattr__(self, name, value):
        """Set port value."""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return
        
        port = self._ports.get(name)
        if port is None:
            raise AttributeError(
                self._error_no_port(name) + "\n"
                f"Hint: Did you mean to add '{name}: OUTPUT[Type]' to the class definition?"
            )
        
        port_type, _ = port
        
        if port_type == 'input':
            raise AttributeError(
                f"Cannot assign to input port '{name}' in module '{self._module_name}'.\n"
                f"Input ports are read-only. They receive values from the parent module."
            )
        
        if port_type == 'output':
            if name not in self._assigned:
                raise AttributeError(
                    f"Output port '{name}' already assigned in module '{self._module_name}'.\n"
                    f"Each output can only be assigned once. Use Mux() for conditional assignment."
                )
            self._assigned.discard(name)
        
        # Type check for output and inout
        if port_type in ('output', 'inout'):
            target_type = self._types.get(name)
            if target_type:
                if not isinstance(value, NexValue):
                    raise TypeError(
                        f"Cannot assign {type(value).__name__} to port '{name}' of module '{self._module_name}'.\n"
                        f"Only NexValues (Logic, Struct, etc.) can be assigned to ports.\n"
                        f"Expected type: {target_type}"
                    )

                actual_type = value.type_like()
                # Compare underlying CIRCT types as Python objects may differ for parameterized types
                if actual_type.type != target_type.type:
                    raise TypeError(
                        f"Type mismatch on port '{name}' of module '{self._module_name}':\n"
                        f"  Expected: {target_type}\n"
                        f"  Got:      {actual_type}"
                    )
        
        self._ports[name] = (port_type, value)
    
    def check_complete(self):
        """Verify all outputs have been assigned."""
        if self._assigned:
            all_outputs = [n for n, (t, _) in self._ports.items() if t == 'output']
            assigned = [n for n in all_outputs if n not in self._assigned]
            raise RuntimeError(
                f"Module '{self._module_name}' build() did not assign all outputs.\n"
                f"Unassigned outputs: {', '.join(self._assigned)}\n"
                f"Assigned outputs: {', '.join(assigned) if assigned else 'none'}\n"
                f"Hint: Add assignments like: io.{next(iter(self._assigned))} = <value>"
            )
    
    def _error_no_port(self, name):
        """Generate error message for non-existent port."""
        return (
            f"Module '{self._module_name}' has no port named '{name}'.\n"
            f"Available ports: {', '.join(self._all_names)}"
        )
    
    @property
    def inputs(self):
        """Get dictionary of input ports."""
        return {n: v for n, (t, v) in self._ports.items() if t == 'input'}
    
    @property
    def outputs(self):
        """Get dictionary of assigned output ports."""
        return {n: v for n, (t, v) in self._ports.items() if t == 'output' and n not in self._assigned}
    
    @property
    def inouts(self):
        """Get dictionary of inout ports."""
        return {n: v for n, (t, v) in self._ports.items() if t == 'inout'}
    
    def __repr__(self):
        by_type = {'input': [], 'output': [], 'inout': []}
        for name, (port_type, _) in self._ports.items():
            by_type[port_type].append(name)
        
        parts = [f"{t}s={names}" for t, names in by_type.items() if names]
        return f"<IO {' '.join(parts)}>"
