"""
Logic Type and Value

Logic represents integer/bit-vector values in hardware.
- LogicType: The type (e.g., Logic[8] for 8-bit)
- Logic: The value wrapper

Usage:
    # Type creation
    Logic[8]        # 8-bit type
    Logic[32]       # 32-bit type
    
    # Value creation
    Logic[8](42)    # Constant
    Logic[8](ir_value)  # Wrap existing
    
    # Operations
    a + b, a - b, a * b, a / b
    a & b, a | b, a ^ b
    a == b, a < b, etc.
"""

from circt.dialects import hw, comb
from circt.extras import types
import circt
from typing import Union, TypeVar

from .base import NexType, NexValue
from ..parameters import is_parameter


T = TypeVar('T', int, 'Logic')



class LogicType(NexType):
    """
    Type class for Logic values with a specific bit width.
    
    Created via: Logic[8], Logic[32], etc.
    """
    
    def __init__(self, bit_width: int):
        """Initialize LogicType with a bit width."""
        if isinstance(bit_width, int):
            if bit_width <= 0:
                raise ValueError(f"Bit width must be positive, got {bit_width}")
        elif not is_parameter(bit_width):
            raise TypeError(f"Bit width must be int or parameter, got {type(bit_width).__name__}")
        
        self.bit_width = bit_width
    
    @property
    def type(self) -> circt.ir.Type:
        """Get the CIRCT integer type."""
        if is_parameter(self.bit_width):
            raise TypeError(
                f"Cannot get CIRCT type from unresolved parameter. "
                f"Resolve parameters first."
            )
        return types.i(self.bit_width)

    def __resolve_parameters__(self, param_dict):
        """Resolve parameters in LogicType."""
        if is_parameter(self.bit_width):
            new_width = self.bit_width.evaluate(param_dict)
            return LogicType(new_width)
        return self
    
    def __call__(self, value=None, **kwargs) -> 'Logic':
        """
        Create a Logic value.
        
        Args:
            value: Can be:
                - None or int: Create constant
                - circt.ir.Value or NexValue: Wrap/cast existing value
        
        Returns:
            Logic instance
        """
        if value is None:
            return self._create_constant(0)
        
        if isinstance(value, int):
            return self._create_constant(value)
        
        # Handle both circt.ir.Value and NexValue
        if isinstance(value, (circt.ir.Value, NexValue)):
            return Logic(self._maybe_cast(value))
        
        raise TypeError(f"Cannot create Logic from {type(value)}")
    
    def _create_constant(self, value: int) -> 'Logic':
        """Create a constant Logic value."""
        return Logic(hw.constant(circt.ir.IntegerAttr.get(self.type, value)))
    
    def __eq__(self, other):
        if not isinstance(other, LogicType):
            return NotImplemented
        return self.bit_width == other.bit_width
    
    def __hash__(self):
        return hash(('LogicType', self.bit_width))
    
    def __repr__(self):
        return f'Logic[{self.bit_width}]'


class Logic(NexValue):
    """
    A class for representing logic/integer values in hardware.
    
    Provides bitwise, arithmetic, and comparison operations.
    Supports signed and unsigned interpretations.
    """
    
    # Comparison predicate mapping
    ICMP_PREDICATE = {
        0: 'eq', 1: 'ne',
        2: 'slt', 3: 'sle', 4: 'sgt', 5: 'sge',
        6: 'ult', 7: 'ule', 8: 'ugt', 9: 'uge',
    }
    
    def __init__(self, value: circt.ir.Value, signed: bool = False):
        """
        Initialize a Logic value.
        
        Args:
            value: The underlying CIRCT IR value (must be IntegerType)
            signed: Whether to use signed arithmetic
        """
        if isinstance(value, int):
            raise ValueError(
                f"Cannot create Logic from int directly. "
                f"Use Logic[width](value) instead."
            )
        
        # Extract IR value if NexValue passed
        if isinstance(value, NexValue):
            value = value.value
        
        if not isinstance(value, circt.ir.Value):
            raise TypeError(f"Expected circt.ir.Value, got {type(value)}")
        
        if not isinstance(value.type, circt.ir.IntegerType):
            raise TypeError(f"Expected IntegerType, got {value.type}")
        
        self._value = value
        self._signed = signed
    
    @property
    def value(self) -> circt.ir.Value:
        """The underlying CIRCT value."""
        return self._value
    
    @property
    def width(self) -> int:
        """The bit width."""
        return self._value.type.width
    
    @property
    def si(self) -> 'Logic':
        """Return a signed view of this value."""
        return Logic(self._value, signed=True)
    
    def is_signed(self) -> bool:
        """Whether this value uses signed arithmetic."""
        return self._signed
    
    def type_like(self) -> LogicType:
        """Return a LogicType matching this value."""
        return LogicType(self.width)
    
    # ==================== Internal Helpers ====================
    
    def _resolve_operand(self, other: T) -> circt.ir.Value:
        """Convert other operand to IR value."""
        if isinstance(other, Logic):
            if self.width != other.width:
                raise ValueError(f"Width mismatch: Logic[{self.width}] != Logic[{other.width}]")
            return other.value
        elif isinstance(other, int):
            if (other + (other < 0)).bit_length() > self.width:
                raise ValueError(f"Integer out of range for Logic[{self.width}]")
            return hw.constant(circt.ir.IntegerAttr.get(self.type, other))
        else:
            raise TypeError(f"Unsupported operand type: {type(other)}")
    
    def _binary_op(self, op, other: T, reverse=False) -> 'Logic':
        """Perform a binary operation."""
        if reverse:
            result = op(self._resolve_operand(other), self._value)
        else:
            result = op(self._value, self._resolve_operand(other))
        return Logic(result)
    
    def _variadic_op(self, op, other: T) -> 'Logic':
        """Perform a variadic operation (add, mul, and, or, xor)."""
        result = op((self._value, self._resolve_operand(other)))
        return Logic(result)
    
    def _cmp_op(self, predicate: int, other: T) -> 'Logic':
        """Perform a comparison operation."""
        pred_attr = circt.ir.IntegerAttr.get(types.i(64), predicate)
        result = comb.icmp(pred_attr, self._value, self._resolve_operand(other))
        return Logic(result)
    
    # ==================== Arithmetic Operations ====================
    
    def __add__(self, other: T) -> 'Logic':
        return self._variadic_op(comb.add, other)
    
    def __sub__(self, other: T) -> 'Logic':
        return self._binary_op(comb.sub, other)
    
    def __mul__(self, other: T) -> 'Logic':
        return self._variadic_op(comb.mul, other)
    
    def __truediv__(self, other: T) -> 'Logic':
        op = comb.divs if self._signed else comb.divu
        return self._binary_op(op, other)
    
    def __floordiv__(self, other: T) -> 'Logic':
        return self._binary_op(comb.divu, other)
    
    def __mod__(self, other: T) -> 'Logic':
        op = comb.mods if self._signed else comb.modu
        return self._binary_op(op, other)
    
    # ==================== Bitwise Operations ====================
    
    def __and__(self, other: T) -> 'Logic':
        return self._variadic_op(comb.and_, other)
    
    def __or__(self, other: T) -> 'Logic':
        return self._variadic_op(comb.or_, other)
    
    def __xor__(self, other: T) -> 'Logic':
        return self._variadic_op(comb.xor, other)
    
    def __lshift__(self, other: T) -> 'Logic':
        return self._binary_op(comb.shl, other)
    
    def __rshift__(self, other: T) -> 'Logic':
        op = comb.shrs if self._signed else comb.shru
        return self._binary_op(op, other)
    
    def __invert__(self) -> 'Logic':
        return self ^ -1
    
    def __neg__(self) -> 'Logic':
        return self * -1
    
    def __pos__(self) -> 'Logic':
        return self
    
    # ==================== Comparison Operations ====================
    
    def __eq__(self, other: T) -> 'Logic':
        return self._cmp_op(0, other)
    
    def __ne__(self, other: T) -> 'Logic':
        return self._cmp_op(1, other)
    
    def __lt__(self, other: T) -> 'Logic':
        return self._cmp_op(2 if self._signed else 6, other)
    
    def __le__(self, other: T) -> 'Logic':
        return self._cmp_op(3 if self._signed else 7, other)
    
    def __gt__(self, other: T) -> 'Logic':
        return self._cmp_op(4 if self._signed else 8, other)
    
    def __ge__(self, other: T) -> 'Logic':
        return self._cmp_op(5 if self._signed else 9, other)
    
    # ==================== Reverse Operations ====================
    
    __radd__ = __add__
    __rmul__ = __mul__
    __rand__ = __and__
    __ror__ = __or__
    __rxor__ = __xor__
    
    def __rsub__(self, other: T) -> 'Logic':
        return self._binary_op(comb.sub, other, reverse=True)
    
    def __rtruediv__(self, other: T) -> 'Logic':
        op = comb.divs if self._signed else comb.divu
        return self._binary_op(op, other, reverse=True)
    
    # ==================== In-place Operations ====================
    
    def __iadd__(self, other: T) -> 'Logic': return self.__add__(other)
    def __isub__(self, other: T) -> 'Logic': return self.__sub__(other)
    def __imul__(self, other: T) -> 'Logic': return self.__mul__(other)
    def __iand__(self, other: T) -> 'Logic': return self.__and__(other)
    def __ior__(self, other: T) -> 'Logic': return self.__or__(other)
    def __ixor__(self, other: T) -> 'Logic': return self.__xor__(other)
    
    # ==================== Concatenation ====================
    
    def __matmul__(self, other: 'Logic') -> 'Logic':
        """Concatenate: a @ b"""
        if not isinstance(other, Logic):
            raise TypeError(f"Concatenation requires Logic, got {type(other)}")
        return Logic(comb.concat((self._value, other._value)))
    
    # ==================== Indexing ====================
    
    def __getitem__(self, index: Union[int, slice]) -> 'Logic':
        """
        Extract bits from the value.
        
        Args:
            index: int for single bit, slice for range
        """
        if isinstance(index, slice):
            return self._slice(index)
        elif isinstance(index, int):
            return self._extract_bit(index)
        else:
            raise TypeError(f"Invalid index type: {type(index)}")
    
    def _extract_bit(self, index: int) -> 'Logic':
        """Extract a single bit."""
        if index < 0:
            index += self.width
        if not 0 <= index < self.width:
            raise IndexError(f"Bit index {index} out of range for width {self.width}")
        return Logic(comb.extract(types.i(1), self._value, index))
    
    def _slice(self, s: slice) -> 'Logic':
        """Extract a range of bits."""
        if s.step is not None:
            raise ValueError("Slice with step is not supported")
        
        # Handle None and negative indices
        start = s.start if s.start is not None else 0
        stop = s.stop if s.stop is not None else self.width
        
        if start < 0:
            start += self.width
        if stop < 0:
            stop += self.width
        
        if not (0 <= start < self.width):
            raise IndexError(f"Start index {start} out of range")
        if not (0 < stop <= self.width):
            raise IndexError(f"Stop index {stop} out of range")
        if start >= stop:
            raise IndexError(f"Start {start} must be less than stop {stop}")
        
        width = stop - start
        return Logic(comb.extract(types.i(width), self._value, start))
    
    # ==================== Bit Manipulation ====================
    
    def zext(self, width: int) -> 'Logic':
        """Zero-extend to width."""
        if width < self.width:
            raise ValueError(f"Cannot zero-extend to smaller width")
        if width == self.width:
            return self
        
        padding = hw.constant(circt.ir.IntegerAttr.get(types.i(width - self.width), 0))
        return Logic(comb.concat((padding, self._value)))
    
    def sext(self, width: int) -> 'Logic':
        """Sign-extend to width."""
        if width < self.width:
            raise ValueError(f"Cannot sign-extend to smaller width")
        if width == self.width:
            return self
        
        sign_bit = comb.extract(types.i(1), self._value, self.width - 1)
        padding = comb.replicate(types.i(width - self.width), sign_bit)
        return Logic(comb.concat((padding, self._value)))
    
    def trunc(self, width: int) -> 'Logic':
        """Truncate to width."""
        if width > self.width:
            raise ValueError(f"Cannot truncate to larger width")
        if width <= 0:
            raise ValueError(f"Width must be positive")
        return Logic(comb.extract(types.i(width), self._value, 0))
    
    def replicate(self, times: int) -> 'Logic':
        """Replicate the value times times."""
        return Logic(comb.replicate(types.i(self.width * times), self._value))
    
    def parity(self) -> 'Logic':
        """Compute parity (XOR of all bits)."""
        return Logic(comb.parity(self._value))

    def reverse(self) -> 'Logic':
        """Reverse the order of bits."""
        return Logic(comb.reverse(self._value))
    
    # ==================== Iteration & Length ====================

    # Disable implicit sequence iteration inherited from __getitem__
    __iter__ = None

    def __len__(self):
        """Disallow len() on Logic; bit width is exposed via .width."""
        raise TypeError("Use .width for bit width of Logic")
    
    # ==================== Class Method ====================
    
    @classmethod
    def __class_getitem__(cls, bit_width: int) -> LogicType:
        """Create a LogicType: Logic[8], Logic[32], etc."""
        from ..parameters import is_parameter
        
        if isinstance(bit_width, int) and bit_width <= 0:
            raise ValueError('Logic bit width must be positive')
        
        if not isinstance(bit_width, int) and not is_parameter(bit_width):
            raise TypeError(f"Logic bit width must be int or parameter, got {type(bit_width).__name__}")
            
        return LogicType(bit_width)
    
    def __repr__(self):
        return f"<Logic[{self.width}]>"
