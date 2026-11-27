# Modules

Modules are the basic building blocks of hardware design in NexHDL. They correspond to `module` in SystemVerilog.

## Basic Module

```python
from nexhdl import *

class Adder(Module):
    a: INPUT[Logic[32]]
    b: INPUT[Logic[32]]
    out: OUTPUT[Logic[32]]

    def build(self, io):
        io.out = io.a + io.b
```

## Ports

Define ports using type annotations with direction wrappers:

```python
class MyModule(Module):
    # Input ports (read-only)
    clk: INPUT[Clock]
    data_in: INPUT[Logic[32]]
    
    # Output ports (write-once)
    data_out: OUTPUT[Logic[32]]
    valid: OUTPUT[Logic[1]]
    
```

### Port Types

- `INPUT[T]` - Read-only input port
- `OUTPUT[T]` - Write-once output port  

Any NexType can be used:
```python
class DataModule(Module):
    # Logic
    enable: INPUT[Logic[1]]
    
    # Array
    data: INPUT[Array[8, Logic[32]]]
    
    # Struct
    packet: INPUT[Packet]
    
    # Ready/Valid Streaming Interface (ESI)
    stream_in:  INPUT[Stream[Logic[32]]]
    stream_out: OUTPUT[Stream[Logic[32]]]
    
    # Nested
    matrix: OUTPUT[Array[4, Array[4, Logic[16]]]]
```

## Build Method

The `build(self, io)` method defines the module's logic:

```python
def build(self, io):
    # Read inputs
    a = io.a
    b = io.b
    
    # Compute
    result = a + b
    
    # Write outputs (once!)
    io.out = result
```

### IO Object

- `io.port_name` - Access ports by name
- Inputs are readable
- Outputs are write-once
- Type-safe access

## Module Hierarchy

Instantiate child modules by calling them with port connections:

```python
class ALU(Module):
    a: INPUT[Logic[32]]
    b: INPUT[Logic[32]]
    op: INPUT[Logic[2]]
    out: OUTPUT[Logic[32]]
    
    def build(self, io):
        io.out = Array[4, Logic[32]]([
            io.a + io.b,
            io.a - io.b,
            io.a & io.b,
            io.a | io.b
        ])[io.op]

class CPU(Module):
    clk: INPUT[Clock]
    inst: INPUT[Logic[32]]
    result: OUTPUT[Logic[32]]
    
    def build(self, io):
        # Instantiate ALU
        alu = ALU(
            a=Logic[32](7),
            b=Logic[32](5),
            op=io.inst[16:18]
        )
        
        # Use ALU output
        io.result = alu.out
    
c = CPU()
print(c.mlir())
print(c.verilog())
```

## Sequential Logic

Use registers with clock contexts:

```python
class Counter(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    enable: INPUT[Logic[1]]
    count: OUTPUT[Logic[32]]
    
    def build(self, io):
        counter = Reg[Logic[32]]()
        
        with io.clk.posedge, io.rst.negedge:
            counter.next = Mux[Logic[32]](
                io.enable,
                counter + 1,
                counter
            )
        
        io.count = counter

```

## Compilation and Output

```python
# Create module
m = Counter()

# Compile to CIRCT IR
m.compile()

# Generate Verilog
verilog = m.verilog()
print(verilog)

# Get MLIR
mlir = m.mlir()

# Simulate
with m.simulate() as sim:
    sim.io.rst = 0
    sim.tick()
    sim.io.rst = 1
    sim.io.enable = 1
    for i in range(10):
        sim.tick()
        print(f"count = {sim.io.count}")
```

## Parameterized Modules

See [Parameterization](parameterization.md) for details.

```python
class Adder[WIDTH](Module):
    a: INPUT[Logic[WIDTH]]
    b: INPUT[Logic[WIDTH]]
    out: OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        io.out = io.a + io.b

# Use with different widths
adder8 = Adder[8]()
adder32 = Adder[32]()

# MLIR
print(adder8.mlir())
print(adder32.mlir())

# Verilog
print(adder8.verilog())
print(adder32.verilog())
```

### Parameter Validation with `Param`

For more advanced validation, use the `Param` class. This allows you to enforce type and value constraints directly in the class definition.

```python
# 1. Define reusable validators
PositiveInt = Param[int](lambda x: x > 0, "Must be positive")
PowerOfTwo  = Param[int](lambda x: x > 0 and (x & (x - 1)) == 0, "Must be a power of two")

# 2. Use as bounds in the generic definition
class Memory[SIZE: PowerOfTwo, WIDTH: PositiveInt](Module):
    addr: INPUT[Logic[clog2(SIZE)]]
    data: OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        mem = Mem[SIZE, Logic[WIDTH]]()
        io.data = mem[io.addr]

# 3. Specialization triggers validation
mem1 = Memory[16, 32]   # Success
mem2 = Memory[15, 32]   # Raises ValueError: Must be a power of two
mem3 = Memory["16", 32] # Raises TypeError: Parameter 'SIZE' must be int
```

Validation occurs at **specialization time** (when you use `[]`), ensuring that only valid hardware configurations are even attempted to be built.

