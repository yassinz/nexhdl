"""
Interface and Bundle Base Classes

Provides grouping of related hardware ports with direction flipping:
- Master / Slave
- Producer / Consumer (ESI-style Source / Sink)
- Flipped
"""

from typing import Dict, Any, Tuple, List
from circt.dialects import hw

from ..core.ports import PortDirection, INPUT, OUTPUT, INOUT
from ..parameters import ParameterizedMeta, ParameterResolver, is_parameter
from ..types.base import to_nex_type, NexType


class InterfaceRole:
    INPUT = "input"
    OUTPUT = "output"
    # Legacy aliases
    MASTER = "output"
    SLAVE = "input"


def _flip_direction(direction):
    if direction == hw.ModulePortDirection.INPUT:
        return hw.ModulePortDirection.OUTPUT
    elif direction == hw.ModulePortDirection.OUTPUT:
        return hw.ModulePortDirection.INPUT
    return direction


class InterfaceMeta(ParameterizedMeta):
    """Metaclass for Interface and Bundle definitions."""
    
    def __new__(mcs, name, bases, namespace):
        # Store port annotations
        port_defs = {}
        for port_name, annotation in namespace.get('__annotations__', {}).items():
            if isinstance(annotation, PortDirection):
                port_defs[port_name] = annotation
        
        namespace['_port_defs'] = port_defs
        cls = super().__new__(mcs, name, bases, namespace)
        return cls

    @property
    def flipped(cls) -> 'InterfacePort':
        """Flipped interface port (INPUT role)."""
        return InterfacePort(cls, role=InterfaceRole.INPUT)

    def _as_port(cls, role: str) -> 'InterfacePort':
        return InterfacePort(cls, role=role)


class InterfacePort:
    """Represents an Interface used as a module port annotation with a specific role."""
    
    def __init__(self, interface_cls, role: str = InterfaceRole.OUTPUT):
        self.interface_cls = interface_cls
        self.role = role

    @property
    def is_flipped(self) -> bool:
        return self.role in (InterfaceRole.INPUT, "slave", "consumer")

    @property
    def is_input(self) -> bool:
        return self.is_flipped

    @property
    def is_output(self) -> bool:
        return not self.is_flipped

    @property
    def flipped(self) -> 'InterfacePort':
        new_role = InterfaceRole.OUTPUT if self.is_flipped else InterfaceRole.INPUT
        return InterfacePort(self.interface_cls, role=new_role)

    def get_flattened_ports(self, prefix: str) -> List[Tuple[str, Any, Any]]:
        """
        Flatten the interface into concrete (port_name, direction, type_obj) tuples.
        """
        flattened = []
        port_defs = getattr(self.interface_cls, '_port_defs', {})
        
        for name, port_dir in port_defs.items():
            full_name = f"{prefix}_{name}"
            direction = port_dir.direction
            if self.is_flipped:
                direction = _flip_direction(direction)
            flattened.append((full_name, direction, port_dir.type_obj))
            
        return flattened

    def __resolve_parameters__(self, param_dict: Dict[str, Any]):
        resolved_cls = ParameterResolver.resolve(self.interface_cls, param_dict)
        if resolved_cls is not self.interface_cls:
            return InterfacePort(resolved_cls, self.role)
        return self

    def __repr__(self):
        dir_name = "INPUT" if self.is_flipped else "OUTPUT"
        return f"{dir_name}[{self.interface_cls.__name__}]"


class InterfaceHandle:
    """
    Runtime handle provided inside build(self, io) to interact with an interface.
    """
    
    def __init__(self, name: str, port_spec: InterfacePort, io_ref):
        self._name = name
        self._spec = port_spec
        self._io = io_ref
        self._ports = {}
        
        # Populate port handles from io
        for port_name in getattr(port_spec.interface_cls, '_port_defs', {}):
            full_name = f"{name}_{port_name}"
            self._ports[port_name] = full_name

    def __getattr__(self, name: str):
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        if name in self._ports:
            full_name = self._ports[name]
            return getattr(self._io, full_name)
        raise AttributeError(f"Interface '{self._name}' has no signal '{name}'")

    def __setattr__(self, name: str, value: Any):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return
        if name in self._ports:
            full_name = self._ports[name]
            setattr(self._io, full_name, value)
            return
        raise AttributeError(f"Interface '{self._name}' has no signal '{name}'")

    def connect(self, other: 'InterfaceHandle'):
        """
        Connect this interface to another complementary interface handle.
        """
        if not isinstance(other, InterfaceHandle):
            raise TypeError(f"Cannot connect {type(other)} to InterfaceHandle")
            
        port_defs = getattr(self._spec.interface_cls, '_port_defs', {})
        for port_name, port_dir in port_defs.items():
            is_self_output = (
                port_dir.direction == hw.ModulePortDirection.OUTPUT and not self._spec.is_flipped
            ) or (
                port_dir.direction == hw.ModulePortDirection.INPUT and self._spec.is_flipped
            )
            
            if is_self_output:
                # Drive other with self
                val = getattr(self, port_name)
                setattr(other, port_name, val)
            else:
                # Drive self with other
                val = getattr(other, port_name)
                setattr(self, port_name, val)

    def __rshift__(self, other: 'InterfaceHandle'):
        """Pipe operator: producer >> consumer."""
        self.connect(other)
        return other

    def __repr__(self):
        return f"<InterfaceHandle '{self._name}' ({self._spec})>"


class Interface(metaclass=InterfaceMeta):
    """
    Base class for defining hardware interfaces and bundles.
    
    Example:
    ```python
    class Stream[T](Interface):
        valid: OUTPUT[Logic[1]]
        ready: INPUT[Logic[1]]
        data:  OUTPUT[T]
    ```
    """
    _handle_class = InterfaceHandle

    @classmethod
    def create_handle(cls, name: str, port_spec: InterfacePort, io_ref) -> InterfaceHandle:
        return cls._handle_class(name, port_spec, io_ref)


# Alias
Bundle = Interface
