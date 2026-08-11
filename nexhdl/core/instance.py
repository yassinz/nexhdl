"""
InstanceHandle - Result of module instantiation
"""


class InstanceHandle:
    """
    Handle for a module instance.
    
    Provides attribute access to output ports.
    """
    
    def __init__(self, module_name, output_names, output_values):
        """
        Initialize instance handle.
        
        Args:
            module_name: Name of the instantiated module
            output_names: List of output port names
            output_values: List of output NexValue objects
        """
        self._module_name = module_name
        self._outputs = dict(zip(output_names, output_values))
    
    def __getattr__(self, name):
        """Get output port value."""
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        
        if name in self._outputs:
            return self._outputs[name]
        
        available = list(self._outputs.keys())
        raise AttributeError(
            f"Instance of '{self._module_name}' has no output port named '{name}'.\n"
            f"Available outputs: {', '.join(available)}"
        )
    
    def __setattr__(self, name, value):
        """Prevent setting attributes (outputs are read-only)."""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return
        
        raise AttributeError(
            f"Cannot assign to output port '{name}' of module instance.\n"
            f"Module outputs are read-only."
        )
    
    @property
    def outputs(self):
        """Get dictionary of all outputs."""
        return self._outputs.copy()
    
    def __repr__(self):
        output_names = list(self._outputs.keys())
        return f"<{self._module_name} instance: outputs={output_names}>"
