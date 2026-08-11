"""
Hardware Multiplexer

Parameterized multiplexer that selects between values based on a selector.

Usage:
    result = Mux[Logic[32]](sel, true_val, false_val)
    result = Mux[Point](sel, point_a, point_b)
    result = Mux[Array[16, Logic[8]]](sel, arr1, arr2)
"""

from circt.dialects import comb
from ..types.base import NexValue, to_nex_type
from ..types.logic import Logic

class MuxType:
    """Type descriptor for parameterized Mux."""
    
    def __init__(self, data_type):
        # Validate immediately - catch generic types without parameters
        if hasattr(data_type, '__type_params__') and data_type.__type_params__:
            raise TypeError(
                f"Cannot use generic type {data_type.__name__} without parameters. "
                f"Use {data_type.__name__}[...] with concrete type parameters."
            )
        self._data_type = to_nex_type(data_type)
    
    def __call__(self, sel, true_val: NexValue, false_val: NexValue) -> NexValue:
        """
        2:1 Hardware multiplexer.
        
        Args:
            sel: Logic[1] selector (1 = true_val, 0 = false_val)
            true_val: Value when sel is 1
            false_val: Value when sel is 0
        
        Returns:
            Selected value (same type as inputs)
        """
        
        if not isinstance(sel, Logic):
            raise TypeError(f"sel must be Logic, got {type(sel).__name__}")
        
        if sel.width != 1:
            raise TypeError(f"sel must be Logic[1], got Logic[{sel.width}]")
        
        # Convert inputs if they are not already NexValues
        # Auto-convert inputs to target type (e.g. integer to Logic, 0 to Struct)
        if not isinstance(true_val, NexValue):
            true_val = self._data_type(true_val)

        if not isinstance(false_val, NexValue):
            false_val = self._data_type(false_val)
        
        # Check type match with parameterized type
        expected_type = self._data_type.type
        
        if true_val.type != expected_type:
            true_type_name = true_val.type_like()
            raise TypeError(
                f"true_val type mismatch: expected {self._data_type}, got {true_type_name}"
            )
        
        if false_val.type != expected_type:
            false_type_name = false_val.type_like()
            raise TypeError(
                f"false_val type mismatch: expected {self._data_type}, got {false_type_name}"
            )
        
        result = comb.mux(sel.value, true_val.value, false_val.value)
        return self._data_type(result)
    
    def __repr__(self):
        return f"Mux[{self._data_type}]"


class Mux:
    """
    **Mux factory: Mux[T]()**
        
    Examples:
    ```python
    result = Mux[32](sel, a, b)         # Shorthand for Mux[Logic[32]]
    result = Mux[Logic[32]](sel, a, b)  # Mux logic
    result = Mux[Point](sel, p1, p2)    # Mux struct
    result = Mux[Array[4, 32]](sel, arr1, arr2)  # Mux array
    ```
    """
    def __init__(self):
        raise TypeError("Mux is not instantiable. Use Mux[...] to get a MuxType.")
    
    def __new__(cls, *args, **kwargs):
        raise TypeError("Mux is not instantiable. Use Mux[...] to get a MuxType.")
    
    def __class_getitem__(cls, data_type) -> MuxType:
        """
        Create MuxType: Mux[Logic[32]], Mux[Point], etc.
        
        Args:
            data_type: The type to multiplex
        
        Returns:
            MuxType
        """
        return MuxType(data_type)
