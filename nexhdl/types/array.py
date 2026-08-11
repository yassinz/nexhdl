"""
Array Type and Value

Arrays are fixed-size collections of homogeneous elements.
Element type can be any NexType: Logic, Struct, another Array, etc.

Usage:
    # Type creation
    Array[8, Logic[32]]           # 8 elements of 32-bit logic
    Array[4, Point]               # 4 Point structs
    Array[16, Array[8, Logic[8]]] # Nested: 16x8 matrix
    
    # Value creation
    Array[4, Logic[8]]([0, 1, 2, 3])
    Array[4, Logic[8]](ir_value)
    
    # Indexing
    arr[0]          # Returns element (Logic, Struct, or inner Array)
    arr[Logic[2]]   # Dynamic index
"""

from math import log2, ceil
from circt.dialects import hw, comb
from circt.extras import types
import circt
from typing import Union, List

from .logic import Logic, LogicType
from .base import NexType, NexValue, to_nex_type
from ..parameters import is_parameter, ParameterResolver




class ArrayType(NexType):
    """
    Type class for fixed-size arrays.
    
    Created via: Array[size, element_type]
    
    Element type can be:
    - LogicType: Array[8, Logic[32]]
    - Struct class: Array[4, Point]
    - ArrayType: Array[16, Array[8, Logic[8]]]
    - int (shorthand for Logic): Array[4, 8] = Array[4, Logic[8]]
    """
    
    def __init__(self, size: int, elem_type: Union[NexType, int]):
        """Initialize ArrayType."""        
        # Validate size
        if isinstance(size, int) and size <= 0:
            raise ValueError(f"Array size must be positive, got {size}")
        if not isinstance(size, int) and not is_parameter(size):
            raise TypeError(f"Array size must be int or parameter, got {type(size).__name__}")
        
        # Validate generic types have parameters
        if not isinstance(elem_type, int) and not is_parameter(elem_type):
            if hasattr(elem_type, '__type_params__') and elem_type.__type_params__:
                raise TypeError(
                    f"Cannot use generic type {elem_type.__name__} without parameters. "
                    f"Use {elem_type.__name__}[...] with concrete type parameters."
                )
        
        # Normalize element type
        if not is_parameter(elem_type):
            elem_type = self._normalize_elem_type(elem_type)
        
        self._size = size
        self._elem_type = elem_type
    
    def _normalize_elem_type(self, elem_type) -> NexType:
        """Convert various type specifications to NexType."""
        return to_nex_type(elem_type)
    
    @property
    def type(self) -> circt.ir.Type:
        """Get the CIRCT ArrayType."""
        
        if is_parameter(self._size):
            raise TypeError("Cannot get CIRCT type from unresolved parameter.")
        
        # Normalize element type
        elem = self._elem_type
        if isinstance(elem, int):
            elem = LogicType(elem)
        elif hasattr(elem, '_nex_type'):
            elem = elem._nex_type
        return hw.ArrayType.get(elem.type, self._size)
    
    @property
    def size(self) -> int:
        """Number of elements."""
        return self._size
    
    @property
    def elem_type(self) -> NexType:
        """Element type."""
        # Normalize if still int
        if isinstance(self._elem_type, int):
            return LogicType(self._elem_type)
        if hasattr(self._elem_type, '_nex_type'):
            return self._elem_type._nex_type
        return self._elem_type
    
    def __call__(self, value=None, **kwargs) -> 'Array':
        """
        Create an Array value.
        
        Args:
            value: Can be:
                - circt.ir.Value or NexValue: Wrap existing array value
                - List of values: Construct from elements
                - None: Zero-initialize
        
        Returns:
            Array instance
        """
        if value is None or (isinstance(value, int) and value == 0):
            return self._create_zero()

        if isinstance(value, (circt.ir.Value, NexValue)):
            return self._wrap_ir_value(value)
        
        if isinstance(value, (list, tuple)):
            return self._create_from_list(value)
        
        raise TypeError(f"Cannot create Array from {type(value)}")
    
    def _wrap_ir_value(self, value) -> 'Array':
        """Wrap an existing CIRCT array value or NexValue."""
        value = self._maybe_cast(value)
        return Array(value, self.elem_type)
    
    def _create_zero(self) -> 'Array':
        """Create zero-initialized array."""
        elem = self.elem_type  # Use property for normalization
        elements = [elem.zero().value for _ in range(self._size)]
        # Use natural order: first element (index 0) is at the highest CIRCT index (MSB)
        ir_value = hw.array_create(self.type, elements)
        return Array(ir_value, elem)
    
    def _create_from_list(self, values: list) -> 'Array':
        """Create array from list of values."""
        if len(values) != self._size:
            raise ValueError(f"Expected {self._size} elements, got {len(values)}")
        
        elem = self.elem_type  # Use property for normalization
        ir_values = []
        for v in values:
            if isinstance(v, int):
                if isinstance(elem, LogicType):
                    if (v + (v < 0)).bit_length() > elem.bit_width:
                        raise ValueError(
                            f"Integer {v} out of range for Array element ({elem})"
                        )
                ir_values.append(elem(v).value)
            elif isinstance(v, NexValue):
                if v.type != elem.type:
                    raise TypeError(
                        f"Element type mismatch: expected {elem}, "
                        f"got {v}"
                    )
                ir_values.append(v.value)
            else:
                raise TypeError(f"Invalid element type: {type(v)}")
        
        # Use natural order: first element (index 0) is at the highest CIRCT index (MSB)
        ir_value = hw.array_create(self.type, ir_values)
        return Array(ir_value, elem)
    
    def __resolve_parameters__(self, param_dict):
        """Resolve parameters in ArrayType."""
        
        new_size = self._size.evaluate(param_dict) if is_parameter(self._size) else self._size
        new_elem = ParameterResolver.resolve(self._elem_type, param_dict)
        
        if new_size != self._size or new_elem != self._elem_type:
            return ArrayType(new_size, new_elem)
        return self
    
    def __repr__(self):
        return f'Array[{self._size}, {self._elem_type}]'


class Array(NexValue):
    """
    Array value - a fixed-size collection of elements.
    
    Supports indexing with int or Logic values.
    """
    
    def __init__(self, value: circt.ir.Value, elem_type: NexType):
        """
        Initialize Array from CIRCT value.
        
        Args:
            value: The CIRCT array value
            elem_type: The element NexType
        """
        if not isinstance(value, circt.ir.Value):
            raise TypeError(f"Expected circt.ir.Value, got {type(value)}")
        
        if not hw.ArrayType.isinstance(value.type):
            raise TypeError(f"Expected array value, got {value.type}")
        
        if not isinstance(elem_type, NexType):
            raise TypeError(f"elem_type must be NexType, got {type(elem_type)}")
        
        arr_type = hw.ArrayType(value.type)
        if arr_type.element_type != elem_type.type:
            raise TypeError(
                f"Element type mismatch: value has {arr_type.element_type}, "
                f"but elem_type is {elem_type.type}"
            )
        
        self._value = value
        self._elem_type = elem_type
        self._size = arr_type.size
    
    @property
    def value(self) -> circt.ir.Value:
        """The underlying CIRCT value."""
        return self._value
    
    @property
    def size(self) -> int:
        """Number of elements."""
        return self._size
    
    @property
    def elem_type(self) -> NexType:
        """Element type."""
        return self._elem_type
    
    def type_like(self) -> ArrayType:
        """Return an ArrayType matching this array."""
        return ArrayType(self._size, self._elem_type)
    
    def _index_bits(self) -> int:
        """Required index bit width."""
        return max(1, ceil(log2(self._size)))
    
    def __getitem__(self, index) -> NexValue:
        """
        Get element at index.
        
        Args:
            index: int for static index, Logic for dynamic index
            
        Returns:
            Element value (type determined by elem_type)
        """        
        required_bits = self._index_bits()
        
        if isinstance(index, int):
            if not 0 <= index < self._size:
                raise IndexError(
                    f"Array index {index} out of range for Array[{self._size}, ...]\n"
                    f"Valid range: [0, {self._size})"
                )
            idx_type = circt.ir.IntegerType.get_signless(required_bits)
            idx_value = hw.constant(circt.ir.IntegerAttr.get(idx_type, index))
        
        elif isinstance(index, Logic):
            if index.width != required_bits:
                raise TypeError(
                    f"Array index width mismatch for Array[{self._size}, ...]:\n"
                    f"  Expected: Logic[{required_bits}]\n"
                    f"  Got:      Logic[{index.width}]\n"
                    f"  Hint: Use index[0:{required_bits}] to slice the index"
                )
            idx_value = index.value
        
        else:
            raise TypeError(
                f"Array index must be int or Logic, got {type(index).__name__}"
            )
        
        # Transform logical index i to CIRCT index (size - 1 - i)
        # This is because we store the first element at the highest index
        required_bits = self._index_bits()
        idx_type = circt.ir.IntegerType.get_signless(required_bits)
        size_minus_1 = hw.constant(circt.ir.IntegerAttr.get(idx_type, self._size - 1))
        actual_idx = comb.sub(size_minus_1, idx_value)
        
        # Get element and wrap with element type
        result = hw.array_get(self._value, actual_idx)
        return self._elem_type(result)
    
    def __setitem__(self, index, element) -> None:
        """
        Set element at index (functional update - creates new array internally).
        
        Args:
            index: int or Logic
            element: New element value
        """
        from .logic import Logic
        
        required_bits = self._index_bits()
        
        if isinstance(index, int):
            if not 0 <= index < self._size:
                raise IndexError(f"Index {index} out of range [0, {self._size})")
            idx_type = circt.ir.IntegerType.get_signless(required_bits)
            idx_value = hw.constant(circt.ir.IntegerAttr.get(idx_type, index))
        
        elif isinstance(index, Logic):
            if index.width != required_bits:
                raise TypeError(
                    f"Index width must be {required_bits}, got {index.width}"
                )
            idx_value = index.value
        
        else:
            raise TypeError(f"Invalid index type: {type(index)}")
        
        # Transform logical index i to CIRCT index (size - 1 - i)
        required_bits = self._index_bits()
        idx_type = circt.ir.IntegerType.get_signless(required_bits)
        size_minus_1 = hw.constant(circt.ir.IntegerAttr.get(idx_type, self._size - 1))
        actual_idx = comb.sub(size_minus_1, idx_value)
        
        if not isinstance(element, NexValue):
            raise TypeError(f"Element must be NexValue, got {type(element)}")
        
        if element.type != self._elem_type.type:
            raise TypeError(
                f"Element type mismatch: expected {self._elem_type.type}, "
                f"got {element.type}"
            )
        
        # Functional update
        self._value = hw.array_inject(self._value, actual_idx, element.value)
    
    def slice(self, low: int, length: int) -> 'Array':
        """
        Extract a sub-array.
        
        Args:
            low: Starting index
            length: Number of elements
            
        Returns:
            New Array with the slice
        """
        if length <= 0:
            raise ValueError("Slice length must be positive")
        if not 0 <= low < self._size:
            raise IndexError(f"Low index {low} out of range")
        if low + length > self._size:
            raise IndexError(f"Slice [{low}:{low+length}] exceeds array size {self._size}")
        
        required_bits = self._index_bits()
        idx_type = circt.ir.IntegerType.get_signless(required_bits)
        # Logical range [low, low+length-1] maps to CIRCT range [size-low-length, size-1-low]
        actual_low_idx = hw.constant(circt.ir.IntegerAttr.get(idx_type, self._size - low - length))
        
        result_type = hw.ArrayType.get(self._elem_type.type, length)
        result = hw.array_slice(self._value, actual_low_idx, result_type)
        return Array(result, self._elem_type)
    
    @staticmethod
    def concat(*arrays: 'Array') -> 'Array':
        """
        Concatenate multiple arrays.
        
        Args:
            *arrays: Arrays to concatenate (must have same element type)
            
        Returns:
            New Array with all elements
        """
        if len(arrays) < 1:
            raise ValueError("concat requires at least one array")
        
        elem_types = {a._elem_type for a in arrays}
        if len(elem_types) != 1:
            raise TypeError("All arrays must have the same element type")
        
        elem_type = next(iter(elem_types))
        total_size = sum(a._size for a in arrays)
        
        result_type = hw.ArrayType.get(elem_type.type, total_size)
        result = hw.array_concat([a._value for a in arrays], result_type)
        return Array(result, elem_type)
    
    def __len__(self):
        return self._size
    
    def __iter__(self):
        """Iterate over elements."""
        for i in range(self._size):
            yield self[i]
    
    @classmethod
    def __class_getitem__(cls, args) -> ArrayType:
        """
        Create ArrayType: Array[size, element_type]
        """
        if isinstance(args, tuple) and len(args) == 2:
            size, elem_type = args
            return ArrayType(size, elem_type)
        else:
            raise ValueError(f"Array requires [size, element_type], got {args}")
    
    def __repr__(self):
        return f"<Array[{self._size}, {self._elem_type}]>"
