"""
Port Direction Annotations
"""

from circt.dialects import hw
from ..types import to_nex_type
from ..parameters import ParameterResolver, is_parameter



class PortDirection:
    """Base class for port direction annotations."""
    
    def __init__(self, direction, type_obj=None):
        self.direction = direction
        self.type_obj = type_obj

    def __resolve_parameters__(self, param_dict):
        """Resolve parameters within the port type."""
        new_type = ParameterResolver.resolve(self.type_obj, param_dict)
        # Use indexing to reuse normalization logic in __class_getitem__
        return self.__class__[new_type] if new_type is not self.type_obj else self
    
    def __class_getitem__(cls, type_obj):
        """Allow [Type] syntax for types and interfaces."""
        if is_parameter(type_obj):
            return cls(type_obj)

        from ..interfaces.base import Interface, InterfacePort, InterfaceRole
        if isinstance(type_obj, type) and issubclass(type_obj, Interface):
            role = InterfaceRole.OUTPUT if cls._direction == hw.ModulePortDirection.OUTPUT else InterfaceRole.INPUT
            return InterfacePort(type_obj, role=role)

        if isinstance(type_obj, InterfacePort):
            role = InterfaceRole.OUTPUT if cls._direction == hw.ModulePortDirection.OUTPUT else InterfaceRole.INPUT
            return InterfacePort(type_obj.interface_cls, role=role)

        return cls(to_nex_type(type_obj))
    
    def __repr__(self):
        direction_name = {
            hw.ModulePortDirection.INPUT: "INPUT",
            hw.ModulePortDirection.OUTPUT: "OUTPUT",
        }.get(self.direction, "UNKNOWN")
        
        if self.type_obj:
            return f"{direction_name}[{self.type_obj}]"
        return direction_name


class INPUT(PortDirection):
    """Input port. Use INPUT[Type]."""
    _direction = hw.ModulePortDirection.INPUT
    
    def __init__(self, type_obj=None):
        super().__init__(self._direction, type_obj)


class OUTPUT(PortDirection):
    """Output port. Use OUTPUT[Type]."""
    _direction = hw.ModulePortDirection.OUTPUT
    
    def __init__(self, type_obj=None):
        super().__init__(self._direction, type_obj)

