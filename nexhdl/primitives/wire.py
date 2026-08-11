"""
Wire - Hardware Wire (Dynamic Subclassing Implementation)

Wires are stateless elements that transmit values.
Use Wire[T]() to create a named wire that can be assigned later.

Usage:
    w = Wire[Logic[32]]()
    io.out = w  # Use before assignment
    w.assign = a + b  # Assign later
"""
from ..types.base import NexValue, to_nex_type, get_value_class
from ..types.logic import LogicType
from ..core.context import get_current_context

_WIRE_CLASS_CACHE = {}


def _create_wire_class(ValueClass, data_type):
    """Dynamically create a Wire class that inherits from ValueClass."""
    cache_key = (ValueClass, hash(data_type))
    if cache_key in _WIRE_CLASS_CACHE:
        return _WIRE_CLASS_CACHE[cache_key]
    
    def assign_getter(self):
        raise AttributeError("Wire.assign is write-only. Use 'wire.assign = value'.")
    
    def assign_setter(self, value):
        """Assign value to the wire."""
        if self._wire_is_assigned:
            raise RuntimeError("Wire can only be assigned once.")
        
        # Get IR value
        if hasattr(value, '_wire_output_ir'):
            val_ir = value._wire_output_ir
        elif isinstance(value, NexValue):
            val_ir = value.value
        elif isinstance(value, int):
            if not isinstance(self._wire_data_type, LogicType):
                raise TypeError(f"Cannot assign int to Wire of type Wire[{self._wire_data_type}]")
            if (value + (value < 0)).bit_length() > self._wire_data_type.bit_width:
                raise ValueError(f"Integer {value} out of range for Wire[{self._wire_data_type}]")
            val_ir = self._wire_data_type(value).value
        else:
            raise TypeError(
                f"Cannot assign {type(value).__name__} to Wire[{self._wire_data_type}]."
                f" Use Wire.assign = {self._wire_data_type}(...)."
            )
        
        # Type check
        if val_ir.type != self._wire_data_type.type:
            raise TypeError(
                f"Type mismatch in Wire.assign: expected {self._wire_data_type.type}, got {val_ir.type}"
            )
        
        # Replace placeholder with real value
        self._wire_placeholder_ir.replace_all_uses_with(val_ir)
        self._value = val_ir
        self._wire_output_ir = val_ir
        self._wire_is_assigned = True
    
    class_attrs = {
        'assign': property(assign_getter, assign_setter),
        'value': property(lambda self: self._wire_output_ir),
    }
    
    if hasattr(ValueClass, '__annotations__'):
        class_attrs['__annotations__'] = ValueClass.__annotations__.copy()
    if hasattr(ValueClass, '_hw_type'):
        class_attrs['_hw_type'] = ValueClass._hw_type
    
    WireClass = type(f"Wire_{ValueClass.__name__}", (ValueClass,), class_attrs)
    _WIRE_CLASS_CACHE[cache_key] = WireClass
    return WireClass


class WireType:
    """Type descriptor for wires."""
    
    def __init__(self, data_type):
        if hasattr(data_type, '__type_params__') and data_type.__type_params__:
            raise TypeError(f"Generic type {data_type.__name__} needs parameters")
        self._data_type = to_nex_type(data_type)
    
    def __call__(self, name=None):
        """Create a Wire instance."""
        ValueClass = get_value_class(self._data_type)
        placeholder = self._data_type.zero()
        WireClass = _create_wire_class(ValueClass, self._data_type)
        
        instance = object.__new__(WireClass)
        for key, val in placeholder.__dict__.items():
            setattr(instance, key, val)
        
        instance._wire_placeholder_ir = placeholder.value
        instance._wire_output_ir = placeholder.value
        instance._wire_data_type = self._data_type
        instance._wire_is_assigned = False
        
        if name:
            instance.set_name(name)
        
        # Register with context
        ctx = get_current_context()
        if ctx:
            ctx.add_wire(instance)
        
        return instance
    
    def __repr__(self):
        return f"Wire[{self._data_type}]"


class Wire:
    """
    **Wire factory: Wire[T]()**
    
    Examples:
    ```python
    # Create wire
    wire_logic = Wire[Logic[32]]()
    wire_array = Wire[Array[8, Logic[32]]]()
    wire_struct = Wire[Point]()

    # Assign value
    wire_logic.assign = 42
    wire_logic.assign = Logic[32](42)
    wire_array.assign = Array[8, Logic[32]]([Logic[32](i) for i in range(8)])
    wire_struct.assign = Point(x=Logic[32](42), y=Logic[32](42))
    ```
    """
    def __init__(self):
        raise TypeError("Wire is not instantiable. Use Wire[T]() instead.")
    
    def __class_getitem__(cls, data_type) -> WireType:
        return WireType(data_type)
