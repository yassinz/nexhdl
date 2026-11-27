"""
Reg - Hardware Register (Dynamic Subclassing Implementation)

Registers are stateful elements that hold a value across clock cycles.

Key Design: When you create Reg[T](), you get back an instance that:
- IS-A T (inherits from T's value class)
- All of T's operators/methods work naturally
- Adds .next property for state assignment

IMPORTANT: Reg is NOT an NexType. It's a stateful container.
- You CANNOT use Reg in type compositions like Array[8, Reg[32]]

Usage:
    # Create register - returns a Logic instance with .next added
    counter = Reg[Logic[32]]()
    
    # All Logic operations work naturally (inherited!)
    result = counter + 1          # Works! counter IS-A Logic
    io.out = counter              # Works!
    
    # .next for assignment inside clock context
    with clk.posedge:
        counter.next = counter + 1
    
    # Works with any type
    point_reg = Reg[Point]()
    point_reg.x                   # Access field - works!
    point_reg.next = Point(...)   # Assign whole struct
"""

from circt.dialects import seq, hw
import circt

from ..types.base import NexValue, to_nex_type, get_value_class
from ..types.logic import LogicType
from ..types.clock import Clock, Reset
from ..core.context import get_current_context


# Cache for dynamically created Reg classes
_REG_CLASS_CACHE = {}


def _create_reg_class(ValueClass, data_type):
    """Dynamically create a Reg class that inherits from ValueClass."""
    cache_key = (ValueClass, hash(data_type))
    if cache_key in _REG_CLASS_CACHE:
        return _REG_CLASS_CACHE[cache_key]
    
    def next_getter(self):
        raise AttributeError("Reg.next is write-only. Use 'reg.next = value' to assign.")
    
    def next_setter(self, value):
        """Assign the next value for this register."""        
        if self._reg_is_wired:
            raise RuntimeError(
                "Reg.next can only be assigned once. "
                "For conditional assignment, use Mux()."
            )
        
        # Get IR value
        if hasattr(value, '_reg_output_ir'):
            next_ir = value._reg_output_ir
        elif isinstance(value, NexValue):
            next_ir = value.value
        elif isinstance(value, int):
            if not isinstance(self._reg_data_type, LogicType):
                raise TypeError(f"Cannot assign int to Reg of type Reg[{self._reg_data_type}]")
            if (value + (value < 0)).bit_length() > self._reg_data_type.bit_width:
                raise ValueError(f"Integer {value} out of range for Reg[{self._reg_data_type}]")
            next_ir = self._reg_data_type(value).value
        else:
            raise TypeError(
                f"Cannot assign {type(value).__name__} to Reg[{self._reg_data_type}]. "
                f" Use Reg.next = {self._reg_data_type}(...)."
            )
        
        # Type check
        if next_ir.type != self._reg_data_type.type:
            raise TypeError(
                f"Type mismatch in Reg.next: expected {self._reg_data_type.type}, got {next_ir.type}"
            )
        
        # Get clock/reset from context
        if not Clock.ACTIVE_CLOCKS:
            raise RuntimeError("Reg.next must be assigned inside a clock context.")
        
        clock = Clock.get_active()
        reset = Reset.get_active()
        
        # Build compreg
        if reset is not None:
            reset_val = (self._reg_reset_value.value if self._reg_reset_value is not None
                        else self._reg_data_type.zero().value)
            new_output = seq.compreg(next_ir, clock.value, reset=reset.value, reset_value=reset_val)
        else:
            new_output = seq.compreg(next_ir, clock.value)
        
        # Set initial value attribute if provided
        if self._reg_init is not None:
            init_attr = self._extract_init_attr()
            if init_attr:
                new_output.owner.attributes['initialValue'] = init_attr
        
        self._reg_placeholder_ir.replace_all_uses_with(new_output)
        self._value = new_output
        self._reg_output_ir = new_output
        self._reg_is_wired = True
    
    def _extract_init_attr(self):
        """Extract attribute from constant for initial_value."""
        init_ir = self._reg_init.value
        if hasattr(init_ir, 'owner') and 'constant' in init_ir.owner.name:
            return init_ir.owner.attributes['value']
        return None
    
    class_attrs = {
        'next': property(next_getter, next_setter),
        'value': property(lambda self: self._reg_output_ir),
        '_extract_init_attr': _extract_init_attr,
    }
    
    if hasattr(ValueClass, '__annotations__'):
        class_attrs['__annotations__'] = ValueClass.__annotations__.copy()
    if hasattr(ValueClass, '_hw_type'):
        class_attrs['_hw_type'] = ValueClass._hw_type
    
    RegClass = type(f"Reg_{ValueClass.__name__}", (ValueClass,), class_attrs)
    _REG_CLASS_CACHE[cache_key] = RegClass
    return RegClass




class RegType:
    """
    Type descriptor for registers.
    
    NOT an NexType - Reg is special and cannot be composed.
    """
    
    def __init__(self, data_type):
        """
        Initialize RegType.
        
        Args:
            data_type: The type held by the register
                - NexType (LogicType, ArrayType, etc.)
                - Struct/Union class
                - int (shorthand for Logic[int])
        """
        # Validate generic types have parameters
        if hasattr(data_type, '__type_params__') and data_type.__type_params__:
            raise TypeError(
                f"Cannot use generic type {data_type.__name__} without parameters. "
                f"Use {data_type.__name__}[...] with concrete type parameters."
            )
        self._data_type = to_nex_type(data_type)
    
    @property
    def data_type(self):
        """The NexType held by this register."""
        return self._data_type
    
    def __call__(self, init=None):
        """
        Create a Reg instance.
        
        Args:
            init: Initial and reset value (int or NexValue)
        
        Returns:
            An instance of dynamically-created Reg class (IS-A held type)
        """
        # Convert and validate init
        if init is not None:
            init = self._convert_value(init, "Init")
        
        # Create instance
        ValueClass = get_value_class(self._data_type)
        placeholder = self._data_type.zero()
        RegClass = _create_reg_class(ValueClass, self._data_type)
        
        instance = object.__new__(RegClass)
        for key, val in placeholder.__dict__.items():
            setattr(instance, key, val)
        
        instance._reg_placeholder_ir = placeholder.value
        instance._reg_output_ir = placeholder.value
        instance._reg_data_type = self._data_type
        instance._reg_is_wired = False
        instance._reg_init = init
        instance._reg_reset_value = init
        
        # Register with context
        ctx = get_current_context()
        if ctx:
            ctx.add_reg(instance)
        
        return instance
    
    def _convert_value(self, value, name):
        """Convert int to NexValue and validate type."""
        if isinstance(value, int):
            return self._data_type(value)
        elif isinstance(value, NexValue):
            if value.type != self._data_type.type:
                raise TypeError(
                    f"{name} type mismatch: expected {self._data_type.type}, got {value.type}"
                )
            return value
        else:
            raise TypeError(f"{name} must be int or NexValue, got {type(value).__name__}")
    
    def __repr__(self):
        return f"Reg[{self._data_type}]"


class Reg():
    """
    **Register factory: Reg[T]()**
    
    Examples:
    ```python
    # Create register
    counter = Reg[32](init=0)
    
    counter = Reg[32]()             # Shorthand for Logic[32]
    counter = Reg[Logic[32]]()      # Returns Logic-like with .next
    point_reg = Reg[Point]()        # Returns Point-like with .next
    array_reg = Reg[Array[4, 32]]() # Returns Array-like with .next

    # Register will use clock and reset from context
    with io.clk.posedge, io.rst.negedge:
        counter.next = counter + 1
        point_reg.next = Point(x=42, y=42)
        array_reg.next = Array[4, 32]([1, 2, 3, 4])
    ```
    """
    def __init__(self):
        raise TypeError("Reg is not instantiable. Use Reg[T]() instead.")
    
    def __class_getitem__(cls, data_type) -> RegType:
        """
        Create RegType: Reg[Logic[32]], Reg[Point], Reg[32], etc.
        
        Args:
            data_type: The type to hold in the register
        
        Returns:
            RegType (NOT an NexType - cannot be composed)
        """
        return RegType(data_type)
