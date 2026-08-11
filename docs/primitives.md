# Primitives

Primitives are fundamental building blocks used to construct hardware logic.

## Reg - Registers

Registers hold state across clock cycles. `Reg[T]()` returns an object that IS-A `T` with a `.next` property for assignment.

### Basic Usage

```python
# Create register
count = Reg[Logic[32]]()

# Assign in clock context
with io.clk.posedge:
    count.next = count + 1

# Read current value
io.out = count
```

### With Initial Value

```python
# For simulation
reg = Reg[Logic[32]](init=42)
```

### Works with Any Type

```python
# Array register
arr_reg = Reg[Array[4, Logic[8]]]()

# Struct register
class Point(Struct):
    x: Logic[16]
    y: Logic[16]

point_reg = Reg[Point]()

with io.clk.posedge:
    point_reg.next = Point(x=io.x, y=io.y)
    # Access fields
    io.out_x = point_reg.x
```

### Key Points

- **IS-A relationship**: `Reg[Logic[32]]()` IS-A `Logic[32]`
- All operators work: `reg + 1`, `reg & mask`, etc.
- `.next` is write-only, use inside clock context
- Single assignment per clock cycle

## Wire - Wires

Wires allow forward declaration and late assignment. Useful for breaking circular dependencies.

### Basic Usage

```python
# Declare wire
result = Wire[Logic[32]]()

# Use before assignment
io.out = result

# Assign later
result.assign = io.a + io.b
```

### Complex Example

```python
class Datapath(Struct):
    alu: Logic[32]
    mem: Logic[32]
    pc: Logic[32]

# Declare
datapath = Wire[Datapath]()

# Use in multiple places
io.out1 = datapath.alu
io.out2 = datapath.pc

# Compute values
alu_result = io.a + io.b
mem_result = memory[io.addr]
pc_result = pc_reg + 4

# Assign once
datapath.assign = Datapath(
    alu=alu_result,
    mem=mem_result,
    pc=pc_result
)
```

### Key Points

- **IS-A relationship**: `Wire[Logic[32]]()` IS-A `Logic[32]`
- `.assign` is write-only property
- Single assignment only
- Works with any type

## Mux - Multiplexer

Select between values based on condition.

### Basic Usage

```python
# Mux[Type](selector, true_value, false_value)
result = Mux[Logic[32]](sel, a, b)

# Equivalent to: result = sel ? a : b
```

### Examples

```python
# Simple enable
out = Mux[Logic[8]](enable, data, Logic[8](0))

# With structs
point = Mux[Point](valid, new_point, old_point)

# Nested mux (4:1)
result = Mux[Logic[32]](
    sel[0],
    Mux[Logic[32]](sel[1], a, b),
    Mux[Logic[32]](sel[1], c, d)
)

# Priority encoder
result = Mux[Logic[32]](
    high_priority,
    high_data,
    Mux[Logic[32]](
        low_priority,
        low_data,
        default_data
    )
)
```

### Key Points

- Type must be specified: `Mux[Logic[32]]`
- Selector must be `Logic[1]`
- Both values must match the specified type
- Works with any type

## Map - Lookup Table

A Map provides a hardware lookup table that selects a value based on an exact match of the key. It supports priority matching if multiple patterns overlap (first entry has highest priority).

### Basic Usage

```python
# Create a map with 4-bit keys and 32-bit values
lookup_table = Map[4, 32](
    (0b0001, 10),
    (0b0010, 71),
    (0b0110, 41),
    (0b1110, 56),
    default=0
)

# Use the map to lookup a value based on an input key
io.out = lookup_table[io.key]
```

### Advanced Usage

```python
# Custom types in maps
class ControlSignals(Struct):
    en: Logic[1]
    op: Logic[2]

# Map that returns structs
decoder = Map[Logic[4], ControlSignals](
    (0b0001, ControlSignals(en=1, op=0)),
    (0b0010, ControlSignals(en=1, op=1)),
    (0b0100, ControlSignals(en=1, op=2)),
    default=ControlSignals(en=0, op=0)
)

io.ctrl = decoder[io.opcode]
```

### Key Points

- `Map[KeyType, ValueType]` - Define keys and values.
- Keys are matched exactly.
- **Priority Matching**: If multiple entries match, the first one provided has the highest priority.
- `default` value is used if no match is found; otherwise, it defaults to zero.
- Works with any combination of types (Logic, Array, Struct).

## Mem - Memory

Memories are fixed-size arrays of stateful elements with read/write access.

### Basic Usage

```python
# Create memory
mem = Mem[16, Logic[32]]()   # 16 entries of 32-bit

with io.clk.posedge, io.rst.negedge:
    # Read via indexing
    io.out = mem[io.addr]
    
    # Write with enable
    mem.write(io.addr, io.data, io.we)
```

### Read with Enable

```python
with io.clk.posedge:
    # Read with enable signal
    io.out = mem.read(io.addr, io.re)
```

### Works with Any Type

```python
# Struct memory
class Point(Struct):
    x: Logic[16]
    y: Logic[16]

mem = Mem[64, Point]()

with io.clk.posedge:
    point = mem[io.addr]
    io.x = point.x
    io.y = point.y
    
    mem.write(io.addr, Point(x=io.x_in, y=io.y_in), io.we)

# Array memory
mem = Mem[8, Array[4, Logic[8]]]()

with io.clk.posedge:
    io.out = mem[io.addr]
    mem.write(io.addr, io.data, io.we)
```

### Parameterized Memory

```python
class RAM[SIZE, WIDTH](Module):
    clk:  INPUT[Clock]
    rst:  INPUT[Reset]
    we:   INPUT[Logic[1]]
    addr: INPUT[Logic[clog2(SIZE)]]
    din:  INPUT[Logic[WIDTH]]
    dout: OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        mem = Mem[SIZE, Logic[WIDTH]]()
        
        with io.clk.posedge, io.rst.negedge:
            io.dout = mem[io.addr]
            mem.write(io.addr, io.din, io.we)
```

### Key Points

- `Mem[SIZE, T]()` - SIZE entries of type T
- Address width is auto-computed: `clog2(SIZE)`
- Read via `mem[addr]` or `mem.read(addr, enable)`
- Write via `mem.write(addr, data, enable)`
- Must be accessed inside clock context
- Works with any NexType

## Fifo - FIFO Queue

FIFOs are first-in-first-out queues with push/pop operations.

### Basic Usage

```python
# Create FIFO
fifo = Fifo[8, Logic[32]]()   # depth=8, 32-bit data

with io.clk.posedge, io.rst.negedge:
    # Push data with write enable
    fifo.push(io.data_in, io.we)
    
    # Pop data with read enable
    io.data_out = fifo.pop(io.re)
    
    # Status flags
    io.full = fifo.full
    io.empty = fifo.empty
```

### Almost Full/Empty Thresholds

```python
# Custom thresholds
fifo = Fifo[16, Logic[32]](
    almost_full=14,     # Signal when 14+ items
    almost_empty=2,     # Signal when 2 or fewer items
    rd_latency=1        # Read latency cycles
)

with io.clk.posedge:
    fifo.push(io.din, io.we)
    io.dout = fifo.pop(io.re)
    io.full = fifo.full
    io.empty = fifo.empty
    io.almost_full = fifo.almost_full
    io.almost_empty = fifo.almost_empty
```

### Works with Any Type

```python
# Struct FIFO
class Packet(Struct):
    data: Logic[64]
    valid: Logic[1]

fifo = Fifo[16, Packet]()

with io.clk.posedge:
    fifo.push(Packet(data=io.din, valid=io.valid), io.we)
    packet = fifo.pop(io.re)
    io.dout = packet.data
```

### Key Points

- `Fifo[DEPTH, T]()` - Queue of DEPTH entries of type T
- `fifo.push(data, enable)` - Push data when enabled
- `fifo.pop(enable)` - Pop and return data when enabled
- `fifo.full` / `fifo.empty` - Status flags
- `fifo.almost_full` / `fifo.almost_empty` - Threshold flags
- Must be accessed inside clock context
- Works with any NexType

## Type Compatibility

All primitives work with any NexType:

```python
# Logic
Reg[Logic[32]]()
Wire[Logic[32]]()
Mux[Logic[32]](sel, a, b)
Mem[16, Logic[32]]()
Fifo[8, Logic[32]]()

# Array
Reg[Array[8, Logic[16]]]()
Wire[Array[8, Logic[16]]]()
Mux[Array[8, Logic[16]]](sel, arr1, arr2)
Mem[16, Array[8, Logic[16]]]()
Fifo[8, Array[8, Logic[16]]]()

# Struct
Reg[Point]()
Wire[Point]()
Mux[Point](sel, p1, p2)
Mem[64, Point]()
Fifo[16, Point]()

# Nested
Reg[Array[4, Point]]()
Wire[Array[4, Point]]()
Mux[Array[4, Point]](sel, arr1, arr2)
Mem[16, Array[4, Point]]()
Fifo[8, Array[4, Point]]()
```
