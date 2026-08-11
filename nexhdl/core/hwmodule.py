"""
HWModule - Low-level CIRCT module wrapper
"""

from circt.dialects import hw
import circt

from .instance import InstanceHandle
from ..types.base import NexType, NexValue


class HWModule:
    """Low-level wrapper around CIRCT hw.module."""
    
    instance_idx = 0
    
    def __init__(self, name, ports, private=False, external=False):
        self.name = name
        hw_ports = [hw.ModulePort(circt.ir.StringAttr.get(n), t, d) 
                    for n, d, t in ports]
        module_type = hw.ModuleType.get(hw_ports)
        type_attr = circt.ir.TypeAttr.get(module_type)
        
        self.module_type = hw.ModuleType(type_attr.value)
        
        if external:
            # External module - no body
            self.module = hw.module_extern(name, type_attr, circt.ir.ArrayAttr.get([]))
        else:
            # Regular module with body
            self.module = hw.module(name, type_attr, circt.ir.ArrayAttr.get([]))
        
        if private:
            self.module.attributes["sym_visibility"] = circt.ir.StringAttr.get('private')
    
    def instance(self, **kwargs):
        """Create an instance of this module."""        
        args = []
        
        extra = set(kwargs.keys()) - set(self.input_names)
        if extra:
            raise ValueError(
                f"Unexpected arguments for {self.name}: {extra}\n"
                f"Expected inputs: {list(self.input_names)}"
            )
        
        for name, typ in zip(self.input_names, self.input_types):
            if name not in kwargs:
                raise RuntimeError(
                    f"Missing required input '{name}' for module {self.name}\n"
                    f"Required inputs: {list(self.input_names)}"
                )

            if not isinstance(kwargs[name], NexValue):
                raise TypeError(
                    f"Input '{name}' for module {self.name} must be an NexValue\n"
                    f"Got: {type(kwargs[name])}"
                )
            
            arg = kwargs[name]
            if typ != arg.type:
                # Convert MLIR types to readable NexHDL types
                expected_nex = NexType.from_ir(typ)
                actual_nex = arg.type_like()
                raise TypeError(
                    f"Type mismatch for input '{name}' in module {self.name}:\n"
                    f"  Expected: {expected_nex}\n"
                    f"  Got:      {actual_nex}"
                ) from None
            args.append(arg.value)
        
        idx = HWModule.instance_idx
        HWModule.instance_idx += 1
        
        results = hw.instance(
            self.output_types,
            f"{self.name}_{idx}",
            self.name,
            args,
            self.input_names,
            self.output_names,
            circt.ir.ArrayAttr.get([])
        )
        
        results = results if isinstance(results, circt.ir.OpResultList) else [results]
        
        # Wrap outputs with proper types
        values = []
        for val in results:
            nex_type = NexType.from_ir(val.type)
            values.append(nex_type(val))
        
        return InstanceHandle(self.name, self.output_names, values)
    
    @property
    def arguments(self):
        return self.entry_block.arguments
    
    @property
    def input_names(self):
        return self.module_type.input_names
    
    @property
    def input_types(self):
        return self.module_type.input_types
    
    @property
    def output_names(self):
        return self.module_type.output_names
    
    @property
    def output_types(self):
        return self.module_type.output_types
    
    @property
    def entry_block(self):
        blocks = self.module.body.blocks
        if len(blocks) == 0:
            blocks.append(*self.input_types)
        return blocks[0]
    
    def __repr__(self):
        return f"<HWModule {self.name}>"
