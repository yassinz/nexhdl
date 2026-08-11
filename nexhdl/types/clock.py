"""
Clock and Reset Types

Clocks and resets are special signals for sequential logic.

Usage:
    class Counter(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        out: OUTPUT[Logic[32]]
        
        def construct(io):
            counter = Reg[Logic[32]](init=0)
            with io.clk.posedge:
                counter.next = counter + 1
            io.out = counter
"""

from circt.dialects import seq, hw, comb
import circt
from abc import ABCMeta

from .base import NexType, NexValue
from .logic import Logic

# ============================================================================
# Clock
# ============================================================================

class ClockType(NexType):
    """
    Type class for Clock signals.
    
    There's only one clock type (no width parameter).
    """
    _instance = None
    
    @classmethod
    def get(cls) -> 'ClockType':
        """Get singleton ClockType instance."""
        if cls._instance is None:
            cls._instance = ClockType()
        return cls._instance
    
    @property
    def type(self) -> circt.ir.Type:
        """Get the CIRCT seq.ClockType."""
        return seq.ClockType.get()
    
    def __call__(self, value=None, **kwargs) -> 'Clock':
        """Create a Clock value."""
        return Clock(value)
    
    def zero(self) -> 'Clock':
        """Clock doesn't have a zero value, but needed for interface."""
        raise TypeError("Clock cannot have a zero value")
    
    def __repr__(self):
        return "Clock"


class ClockMeta(ABCMeta):
    """Metaclass for Clock that makes the class usable as a type."""
    
    @property
    def type(cls) -> circt.ir.Type:
        """Clock class has .type property."""
        return seq.ClockType.get()
    
    @property
    def _nex_type(cls) -> ClockType:
        """Get the ClockType singleton."""
        return ClockType.get()


class Clock(NexValue, metaclass=ClockMeta):
    """
    Clock signal value.
    
    Used for sequential logic and register clocking.
    """
    
    # Stack of active clocks (for with statement)
    ACTIVE_CLOCKS = []
    
    def __init__(self, value=None):
        """
        Initialize a Clock.
        
        Args:
            value: Can be:
                - circt.ir.Value of ClockType
                - Logic[1] value (converted to clock)
                - None
        """        
        if value is None:
            self._value = None
        
        elif isinstance(value, Logic):
            if value.width != 1:
                raise ValueError("Clock Logic must be 1 bit wide")
            self._value = seq.to_clock(value.value)
        
        elif isinstance(value, circt.ir.Value):
            if seq.ClockType.isinstance(value.type):
                self._value = value
            else:
                raise TypeError(f"Expected ClockType, got {value.type}")
        
        else:
            raise TypeError(f"Cannot create Clock from {type(value)}")
    
    @property
    def value(self) -> circt.ir.Value:
        """The underlying CIRCT value."""
        return self._value
    
    def type_like(self) -> ClockType:
        """Return ClockType."""
        return ClockType.get()
    
    @property
    def posedge(self) -> 'Clock':
        """Positive edge - returns self."""
        return self
    
    @property
    def negedge(self) -> 'Clock':
        """Negative edge - inverted clock."""
        return Clock(seq.clock_inv(self._value))
    
    def __enter__(self):
        """Enter clock context for sequential logic."""
        Clock.ACTIVE_CLOCKS.append(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit clock context."""
        Clock.ACTIVE_CLOCKS.pop()
    
    def __invert__(self):
        """Invert the clock."""
        return Clock(seq.clock_inv(self._value))
    
    def __truediv__(self, other):
        """Produces a clock divided by a power of two"""
        if not isinstance(other, int):
            raise TypeError("Clock can only be divided by an integer")
        if other < 1:
            raise ValueError("Clock can only be divided by a positive integer")
        if other & (other - 1) != 0:
            raise ValueError("Clock can only be divided by a power of two")
        return Clock(seq.clock_div(self._value, other))
        
    
    @classmethod
    def get_active(cls) -> 'Clock':
        """Get the currently active clock (innermost context)."""
        if not cls.ACTIVE_CLOCKS:
            raise RuntimeError("No active clock context")
        return cls.ACTIVE_CLOCKS[-1]
    
    def __repr__(self):
        return "<Clock>"


# ============================================================================
# Reset
# ============================================================================

class ResetType(NexType):
    """
    Type class for Reset signals.
    
    Reset is represented as a 1-bit logic signal.
    """
    _instance = None
    
    @classmethod
    def get(cls) -> 'ResetType':
        """Get singleton ResetType instance."""
        if cls._instance is None:
            cls._instance = ResetType()
        return cls._instance
    
    @property
    def type(self) -> circt.ir.Type:
        """Get the CIRCT type for reset (i1)."""
        return circt.ir.IntegerType.get_signless(1)
    
    def __call__(self, value=None, **kwargs) -> 'Reset':
        """Create a Reset value."""
        return Reset(value)
    
    def zero(self) -> 'Reset':
        """Zero reset = inactive."""
        return Reset(Logic[1](0))
    
    def __repr__(self):
        return "Reset"


class ResetMeta(ABCMeta):
    """Metaclass for Reset that makes the class usable as a type."""
    
    @property
    def type(cls) -> circt.ir.Type:
        """Reset class has .type property."""
        return circt.ir.IntegerType.get_signless(1)
    
    @property
    def _nex_type(cls) -> ResetType:
        """Get the ResetType singleton."""
        return ResetType.get()


class Reset(NexValue, metaclass=ResetMeta):
    """
    Reset signal value.
    
    Used for resetting sequential logic. Represented as a 1-bit signal.
    Works like Clock - use with context manager for reset context.
    
    Usage:
        with io.clk.posedge, io.rst.negedge:
            # Registers here use clk for clock and rst (active low) for reset
            counter.next = counter + 1
    """
    
    # Stack of active resets (for with statement)
    ACTIVE_RESETS = []
    
    def __init__(self, value=None):
        """
        Initialize a Reset.
        
        Args:
            value: Can be:
                - circt.ir.Value of i1
                - Logic[1] value
                - int (0 or 1)
                - None (inactive)
        """
        if value is None:
            self._value = None
        
        elif isinstance(value, int):
            self._value = Logic[1](value).value
        
        elif isinstance(value, Logic):
            if value.width != 1:
                raise ValueError("Reset must be 1 bit wide")
            self._value = value.value
        
        elif isinstance(value, circt.ir.Value):
            self._value = self.type_like()._maybe_cast(value)
        
        else:
            raise TypeError(f"Cannot create Reset from {type(value)}")
    
    @property
    def value(self) -> circt.ir.Value:
        """The underlying CIRCT value."""
        return self._value
    
    def type_like(self) -> ResetType:
        """Return ResetType."""
        return ResetType.get()
    
    @property
    def posedge(self) -> 'Reset':
        """Active high reset (reset when signal is 1)."""
        return self
    
    @property
    def negedge(self) -> 'Reset':
        """Active low reset (reset when signal is 0)."""
        # Invert the signal: 1 -> 0, 0 -> 1
        one = hw.constant(circt.ir.IntegerAttr.get(circt.ir.IntegerType.get_signless(1), 1))
        return Reset(comb.xor([self._value, one]))
    
    def __enter__(self):
        """Enter reset context for sequential logic."""
        Reset.ACTIVE_RESETS.append(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit reset context."""
        Reset.ACTIVE_RESETS.pop()
    
    @classmethod
    def get_active(cls) -> 'Reset':
        """Get the currently active reset (innermost context), or None if no reset."""
        if not cls.ACTIVE_RESETS:
            return None
        return cls.ACTIVE_RESETS[-1]
    
    def __invert__(self) -> 'Reset':
        """Invert the reset signal."""
        return self.negedge
    
    def __repr__(self):
        return "<Reset>"
