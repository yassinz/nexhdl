"""
NexHDL Type System - Base Classes

This module defines the core contract that ALL NexHDL types must follow.
Following this contract enables infinite composability:
- Array[16, Struct]
- Struct with Array fields
- Reg[any type]
- Mem[N, any type]

The Contract:
- NexType: Has `.type` property (CIRCT type) and is callable to create values
- NexValue: Has `.value` property (CIRCT value) and `.type_like()` method
"""

from abc import ABC, abstractmethod
import circt
from circt.dialects import hw, seq


class NexType(ABC):
    """
    Abstract base class for all NexHDL types.
    
    Every type must implement:
    - .type property: Returns the CIRCT IR type
    - __call__: Creates an NexValue (from IR value, zero, or construction args)
    
    This unified contract enables composability:
        Array[16, Logic[8]]      # ArrayType with LogicType element
        Array[16, Point]         # ArrayType with Struct element  
        Reg[Array[16, Point]]    # RegType holding ArrayType of Struct
    """
    
    @property
    @abstractmethod
    def type(self) -> circt.ir.Type:
        """
        Return the CIRCT IR hardware type.
        
        Returns:
            circt.ir.Type: The CIRCT hardware type for this NexHDL type
        """
        pass
    
    def _maybe_cast(self, value) -> circt.ir.Value:
        """
        Attempt to cast a value to this type if bit widths match.
        
        Args:
            value: The input (CIRCT value or NexValue)
            
        Returns:
            The casted CIRCT value (or original if types match)
            
        Raises:
            ValueError: If bit widths do not match
        """
        
        # Store original for error messages
        original_value = value
        
        # Extract IR value from NexValue
        if isinstance(value, NexValue):
            value = value.value
        
        if not isinstance(value, circt.ir.Value):
            return value
            
        target_type = self.type
        if value.type == target_type:
            return value
            
        # Check bit widths
        target_width = hw.get_bitwidth(target_type)
        value_width = hw.get_bitwidth(value.type)
        
        if target_width != value_width:
            # Get readable type names
            target_name = repr(self)
            source_name = original_value.type_like() if isinstance(original_value, NexValue) else value.type
            source_name = repr(source_name) if hasattr(source_name, '__repr__') else str(source_name)
            
            raise ValueError(
                f"Bit width mismatch: cannot cast {source_name} ({value_width} bits) "
                f"to {target_name} ({target_width} bits)"
            )
            
        # Widths match, perform bitcast
        # hw.bitcast takes (result_type, value)
        op = hw.bitcast(target_type, value)
        return op

    @abstractmethod
    def __call__(self, value=None, **kwargs) -> 'NexValue':
        """
        Create an NexValue instance.
        
        This method handles multiple use cases:
        - __call__(circt_value): Wrap an existing CIRCT IR value
        - __call__() or __call__(0): Create a zero-initialized value
        - __call__(x=..., y=...): Construct from named fields (Struct)
        - __call__([...]): Construct from list (Array)
        
        Args:
            value: Can be circt.ir.Value, int, list, or None
            **kwargs: Named field values for Struct construction
            
        Returns:
            NexValue: The created value instance
        """
        pass
    
    def zero(self) -> 'NexValue':
        """
        Create a zero-initialized value.
        
        Default implementation calls __call__() with no args.
        Types can override for custom zero behavior.
        
        Returns:
            NexValue: Zero-initialized value
        """
        return self()

    def bitwidth(self) -> int:
        """
        Get the bit width of this type.
        
        Returns:
            int: The bit width
        """
        return hw.get_bitwidth(self.type)
    
    @staticmethod
    def from_ir(ir_type):
        """Convert CIRCT type to NexType."""
        # Import here to avoid circular imports during module init
        if isinstance(ir_type, circt.ir.IntegerType):
            from .logic import LogicType
            return LogicType(circt.ir.IntegerType(ir_type).width)
        
        if hw.ArrayType.isinstance(ir_type):
            from .array import ArrayType
            arr = hw.ArrayType(ir_type)
            return ArrayType(arr.size, NexType.from_ir(arr.element_type))
        
        if hw.StructType.isinstance(ir_type):
            from .struct import DynamicStruct
            return DynamicStruct.from_ir(ir_type)
        
        if hw.UnionType.isinstance(ir_type):
            from .union import DynamicUnion
            return DynamicUnion.from_ir(ir_type)
        
        if seq.ClockType.isinstance(ir_type):
            from .clock import ClockType
            return ClockType()
        
        raise TypeError(f"Cannot convert IR type to NexType: {ir_type}")
    
    @staticmethod
    def to_circt(type_hint):
        """Convert type hint to CIRCT type."""
        # NexType instance - use .type property
        if isinstance(type_hint, NexType):
            return type_hint.type
        
        # Class with .type property (e.g., Struct class via metaclass)
        if hasattr(type_hint, 'type') and isinstance(type_hint, type):
            return type_hint.type
        
        # Class with get_hw_type method (backward compat)
        if hasattr(type_hint, 'get_hw_type'):
            return type_hint.get_hw_type()
        
        # Object with _nex_type property
        if hasattr(type_hint, '_nex_type'):
            return type_hint._nex_type.type
        
        raise TypeError(
            f"Cannot convert to CIRCT type: {type_hint!r} (type: {type(type_hint).__name__}). "
            f"Expected NexType, Struct/Union class, or object with .type property."
        )

    def __hash__(self):
        return self.type.__hash__()
    
    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class NexValue(ABC):
    """
    Abstract base class for all NexHDL values.
    
    Every value must implement:
    - .value property: Returns the underlying CIRCT IR value
    - .type_like() method: Returns an NexType matching this value's type
    
    Values also get:
    - .type property: Returns the CIRCT IR type (from the value)
    - .set_name(): Set name hint for generated HDL
    """
    
    @property
    @abstractmethod
    def value(self) -> circt.ir.Value:
        """
        Get the underlying CIRCT IR value.
        
        Returns:
            circt.ir.Value: The CIRCT IR value
        """
        pass
    
    @property
    def type(self) -> circt.ir.Type:
        """
        Get the CIRCT type of this value.
        
        Default implementation gets type from the value.
        
        Returns:
            circt.ir.Type: The CIRCT IR type
        """
        return self.value.type
    
    @abstractmethod
    def type_like(self) -> NexType:
        """
        Return an NexType that matches this value's type.
        
        This is used to create new values of the same type.
        For example: result = a.type_like()(some_ir_value)
        
        Returns:
            NexType: A type matching this value
        """
        pass
    
    def set_name(self, name: str) -> None:
        """
        Set the name hint for this value in the generated HDL.
        
        This affects the variable name in Verilog/VHDL output.
        
        Args:
            name: The name to use as a hint
        """
        if isinstance(self.value.owner, circt.ir.Operation):
            namehint = circt.ir.StringAttr.get(name)
            self.value.owner.attributes['sv.namehint'] = namehint
        self._nex_name = name

    def __bool__(self):
        """Disallow Python truthiness on hardware values."""
        raise TypeError("Use Mux/&/| for hardware conditions")

    def __hash__(self):
        return self.value.__hash__()
    
    def __repr__(self):
        return f"<{self.__class__.__name__}>"


# Helper functions for type conversion
def to_nex_type(type_hint) -> NexType:
    """Convert any type hint to an NexType."""
    # Already an NexType
    if isinstance(type_hint, NexType):
        return type_hint
    
    # Check if it's a generic class that needs parameters
    if hasattr(type_hint, '__type_params__') and type_hint.__type_params__:
        raise TypeError(
            f"Cannot use generic type {type_hint.__name__} without parameters. "
            f"Use {type_hint.__name__}[...] with concrete type parameters."
        )

    # Class with _nex_type property (Struct/Union classes)
    if hasattr(type_hint, '_nex_type'):
        return type_hint._nex_type
    
    # Integer shorthand → Logic
    if isinstance(type_hint, int):
        from .logic import LogicType
        return LogicType(type_hint)
    
    raise TypeError(
        f"Cannot convert to NexType: {type_hint!r}. "
        f"Expected NexType, Struct/Union class, or int."
    )


def get_value_class(data_type: NexType):
    """Get the Python Value Class for a given NexType."""
    from .logic import Logic, LogicType
    from .array import Array, ArrayType
    from .struct import StructType
    from .union import UnionType
    
    if isinstance(data_type, LogicType):
        return Logic
    
    if isinstance(data_type, ArrayType):
        return Array
    
    if isinstance(data_type, StructType):
        return data_type._struct_class
    
    if isinstance(data_type, UnionType):
        return data_type._union_class
    
    # Struct/Union class used directly
    if hasattr(data_type, '_nex_type'):
        return data_type
        
    raise TypeError(f"Cannot determine value class for type: {data_type}")


def wrap(ir_value: circt.ir.Value) -> NexValue:
    """Wrap any CIRCT IR value in the appropriate NexValue."""
    nex_type = NexType.from_ir(ir_value.type)
    return nex_type(ir_value)
