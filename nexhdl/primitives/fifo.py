"""
Fifo - Hardware FIFO Queue Primitive

Usage:
    fifo = Fifo[8, Logic[32]]()
    
    with io.clk.posedge, io.rst.negedge:
        fifo.push(io.data_in, io.we)
        io.data_out = fifo.pop(io.re)
        io.full = fifo.full
        io.empty = fifo.empty
"""

from circt.dialects import seq, hw
import circt

from ..types.base import NexValue, to_nex_type


from ..types.base import NexValue, to_nex_type
from ..types.logic import Logic, LogicType
from ..types.clock import Clock, Reset


class FifoType:
    """Type descriptor for FIFOs. Created by Fifo[DEPTH, T]."""
    
    def __init__(self, depth, data_type):
        if not isinstance(depth, int) or depth <= 0:
            raise ValueError(f"FIFO depth must be positive int, got {depth}")
        
        self._depth = depth
        self._data_type = to_nex_type(data_type)
        
    
    @property
    def depth(self):
        return self._depth
    
    @property
    def data_type(self):
        return self._data_type
    
    def __call__(self, almost_full=None, almost_empty=0, rd_latency=1):
        return FifoInstance(self, almost_full, almost_empty, rd_latency)
    
    def __repr__(self):
        return f"Fifo[{self._depth}, {self._data_type}]"


class FifoInstance:
    """FIFO instance with push/pop operations."""
    
    def __init__(self, fifo_type: FifoType, almost_full, almost_empty, rd_latency):
        self._fifo_type = fifo_type
        self._almost_full = almost_full if almost_full is not None else fifo_type.depth
        self._almost_empty = almost_empty
        self._rd_latency = rd_latency
        self._outputs = None
        
        self._data_width = fifo_type.data_type.bitwidth()
        self._flat_type = circt.ir.IntegerType.get_signless(self._data_width)
        
        # Placeholders for deferred wiring
        self._data_placeholder = None
        self._wr_en_placeholder = None
        self._rd_en_placeholder = None
        self._push_called = False
        self._pop_called = False
    
    def _ensure_fifo(self):
        """Create FIFO with placeholders on first access."""
        if self._outputs is not None:
            return
        
        if not Clock.ACTIVE_CLOCKS:
            raise RuntimeError("FIFO must be used inside a clock context")
        
        clock = Clock.get_active()
        reset = Reset.get_active()
        reset_val = reset.value if reset else Logic[1](0).value
        
        # Create placeholders
        self._data_placeholder = self._fifo_type.data_type.zero().value
        self._wr_en_placeholder = Logic[1](0).value
        self._rd_en_placeholder = Logic[1](0).value
        
        i1 = circt.ir.IntegerType.get_signless(1)
        
        # Bitcast data placeholder if needed
        flat_data = hw.bitcast(self._flat_type, self._data_placeholder) if self._data_placeholder.type != self._flat_type else self._data_placeholder
        
        self._outputs = seq.fifo(
            self._flat_type, i1, i1, i1, i1,
            flat_data,
            self._rd_en_placeholder,
            self._wr_en_placeholder,
            clock.value,
            reset_val,
            self._fifo_type.depth,
            rd_latency=self._rd_latency,
            almost_full_threshold=self._almost_full,
            almost_empty_threshold=self._almost_empty
        )
    
    def push(self, data, enable=None):
        """Push data into FIFO."""
        if self._push_called:
            raise RuntimeError("push() can only be called once")
        
        self._ensure_fifo()
        
        # Convert inputs
        if isinstance(data, int):
            data = self._fifo_type.data_type(data)
        en = Logic[1](1 if enable is None else enable) if isinstance(enable, (int, type(None))) else enable
        
        # Bitcast if needed
        flat_data = hw.bitcast(self._flat_type, data.value) if data.type != self._flat_type else data.value
        
        # Wire up placeholders
        self._data_placeholder.replace_all_uses_with(flat_data)
        self._wr_en_placeholder.replace_all_uses_with(en.value)
        self._push_called = True
    
    def pop(self, enable=None) -> NexValue:
        """Pop data from FIFO."""
        if self._pop_called:
            raise RuntimeError("pop() can only be called once")
        
        self._ensure_fifo()
        
        en = Logic[1](1 if enable is None else enable) if isinstance(enable, (int, type(None))) else enable
        
        # Wire up placeholder
        self._rd_en_placeholder.replace_all_uses_with(en.value)
        self._pop_called = True
        
        return self._fifo_type.data_type(self._outputs.owner.output)
    
    @property
    def output(self) -> NexValue:
        """Read data output (without popping)."""
        self._ensure_fifo()
        return self._fifo_type.data_type(self._outputs.owner.output)
    
    @property
    def full(self) -> Logic:
        """Full flag."""
        self._ensure_fifo()
        return Logic(self._outputs.owner.full)
    
    @property
    def empty(self) -> Logic:
        """Empty flag."""
        self._ensure_fifo()
        return Logic(self._outputs.owner.empty)
    
    @property
    def almost_full(self) -> Logic:
        """Almost full flag."""
        self._ensure_fifo()
        return Logic(self._outputs.owner.almost_full)
    
    @property
    def almost_empty(self) -> Logic:
        """Almost empty flag."""
        self._ensure_fifo()
        return Logic(self._outputs.owner.almost_empty)
    
    @property
    def depth(self):
        return self._fifo_type.depth
    
    @property
    def data_type(self):
        return self._fifo_type.data_type
    
    def __repr__(self):
        return f"<Fifo[{self.depth}, {self.data_type}]>"


class Fifo:
    """
    **FIFO factory: Fifo[DEPTH, T]**
    
    Example:
    ```python
    fifo = Fifo[8, Logic[32]]()(almost_full=7, almost_empty=1, rd_latency=1)
    fifo = Fifo[8, Array[4, Logic[8]]]()
    fifo = Fifo[8, Point]()
    
    with io.clk.posedge, io.rst.negedge:
        fifo.push(io.data_in, io.we)          # Push with enable
        io.dout = fifo.pop(io.re)             # Pop with enable

    io.full = fifo.full                   # Full flag
    io.empty = fifo.empty                 # Empty flag
    io.almost_full = fifo.almost_full     # Almost full flag
    io.almost_empty = fifo.almost_empty   # Almost empty flag
    ```

    """
    def __init__(self):
        raise RuntimeError("Use Fifo[DEPTH, T]() syntax")
    
    def __new__(cls, *args, **kwargs):
        raise TypeError("Use Fifo[DEPTH, T]() syntax")
    
    def __class_getitem__(cls, args) -> FifoType:
        if not isinstance(args, tuple) or len(args) != 2:
            raise TypeError("Fifo requires [DEPTH, T] syntax")
        return FifoType(args[0], args[1])
