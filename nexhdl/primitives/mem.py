"""
Mem - Hardware Memory Primitive

Usage:
    mem = Mem[16, Logic[32]]()       # 16 words of 32-bit
    mem = Mem[64, Point]()           # 64 Point structs
    
    with io.clk.posedge, io.rst.negedge:
        io.out = mem[io.addr]               # Read
        mem.write(io.addr, io.data, io.we)  # Write with enable
"""

from circt.dialects import seq, hw
import circt

from ..types.base import NexType, NexValue, to_nex_type
from ..types.logic import Logic, LogicType
from ..types.clock import Clock, Reset


class MemType:
    """Type descriptor for memories. Created by Mem[SIZE, T]."""
    
    def __init__(self, size, data_type):
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"Memory size must be positive int, got {size}")
        
        self._size = size
        self._data_type = to_nex_type(data_type)
        self._addr_width = max(1, (size - 1).bit_length())
        
    
    @property
    def size(self):
        return self._size
    
    @property
    def data_type(self):
        return self._data_type
    
    @property
    def addr_width(self):
        return self._addr_width
    
    def __call__(self, read_latency: int = 0, write_latency: int = 1, name="mem") -> 'MemInstance':
        if read_latency < 0 or write_latency < 0:
            raise ValueError("Memory latencies must be non-negative")
        
        if write_latency == 0:
            raise ValueError("Memory write latency must be at least 1")
        
        return MemInstance(self, read_latency, write_latency, name)
    
    def __repr__(self):
        return f"Mem[{self._size}, {self._data_type}]"


class MemInstance:
    """Memory instance with read/write operations using seq.hlmem."""
    
    def __init__(self, mem_type: MemType, read_latency: int, write_latency: int, name: str):
        self._mem_type = mem_type
        self._name = name
        self._hlmem = None
        self._read_latency = read_latency
        self._write_latency = write_latency
        
        # Compute data width for bitcasting
        self._data_width = mem_type.data_type.bitwidth()
        self._flat_type = circt.ir.IntegerType.get_signless(self._data_width)
    
    def _ensure_hlmem(self):
        """Lazily create hlmem on first access (requires clock context)."""
        if self._hlmem is not None:
            return
        
        if not Clock.ACTIVE_CLOCKS:
            raise RuntimeError("Memory must be accessed inside a clock context")
        
        clock = Clock.get_active()
        reset = Reset.get_active()
        reset_val = reset.value if reset else Logic[1](0).value
        
        hlmem_type = circt.ir.Type.parse(
            f"!seq.hlmem<{self._mem_type.size}xi{self._data_width}>"
        )
        self._hlmem = seq.hlmem(hlmem_type, clock.value, reset_val, self._name)
    
    def _to_addr(self, addr):
        """Convert address to Logic with correct width."""
        width = self._mem_type.addr_width
        if isinstance(addr, int):
            return Logic[width](addr)
        if isinstance(addr, Logic) and addr.width == width:
            return addr
        raise TypeError(f"Address must be int or Logic[{width}]")
    
    def _to_data(self, data):
        """Convert data to proper NexValue."""
        if isinstance(data, int):
            return self._mem_type.data_type(data)
        if isinstance(data, NexValue) and data.type == self._mem_type.data_type.type:
            return data
        raise TypeError(f"Data must match {self._mem_type.data_type}")
    
    def __getitem__(self, addr) -> NexValue:
        """Read from memory: mem[addr]"""
        return self.read(addr)
    
    def read(self, addr, enable=None) -> NexValue:
        """Read with optional enable signal."""
        self._ensure_hlmem()
        addr = self._to_addr(addr)
        en = Logic[1](1 if enable is None else enable) if isinstance(enable, (int, type(None))) else enable
        
        result = seq.read(self._flat_type, self._hlmem, [addr.value], self._read_latency, rd_en=en.value)
        return self._mem_type.data_type(result)
    
    def write(self, addr, data, enable=None):
        """Write to memory: mem.write(addr, data, enable)"""
        self._ensure_hlmem()
        addr = self._to_addr(addr)
        data = self._to_data(data)
        en = Logic[1](1 if enable is None else enable) if isinstance(enable, (int, type(None))) else enable
        
        # Bitcast to flat integer for hlmem (which only supports integer types)
        flat_data = hw.bitcast(self._flat_type, data.value) if data.type != self._flat_type else data.value
        seq.write(self._hlmem, [addr.value], flat_data, en.value, self._write_latency)
    
    @property
    def size(self):
        return self._mem_type.size
    
    @property
    def data_type(self):
        return self._mem_type.data_type
    
    @property
    def addr_width(self):
        return self._mem_type.addr_width
    
    def __len__(self):
        return self._mem_type.size
    
    def __repr__(self):
        return f"<Mem[{self.size}, {self.data_type}] '{self._name}'>"


class Mem:
    """
    **Memory factory: Mem[SIZE, T]**
    
    Example:
    ```python
    mem = Mem[16, Logic[32]](read_latency=1, write_latency=1, name="Memory")
    mem = Mem[8, Array[4, Logic[8]]]()
    mem = Mem[64, Point]()

    with io.clk.posedge:
        mem.write(io.addr, io.data, io.we) # write with enable
        io.dout = mem.read(io.addr, io.re) # read with enable
        io.dout = mem[io.addr]             # read without enable
    ```

    """
    def __init__(self):
        raise RuntimeError("Use Mem[SIZE, T]() syntax")
    
    def __new__(cls, *args, **kwargs):
        raise TypeError("Use Mem[SIZE, T]() syntax")
    
    def __class_getitem__(cls, args) -> MemType:
        if not isinstance(args, tuple) or len(args) != 2:
            raise TypeError("Mem requires [SIZE, T] syntax")
        return MemType(args[0], args[1])
