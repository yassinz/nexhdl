# Simulation in NexHDL

NexHDL provides a high-performance simulation environment powered by **CIRCT Arc**. It uses JIT (Just-In-Time) compilation to transform your hardware modules into machine code, allowing for incredibly fast execution compared to interpreted simulators.

## Architecture

The simulator follows the **Arcilator** pattern from CIRCT:
1. **Lowering**: The Hardware IR is transformed through the `arc` dialect, which optimizes the module for software simulation.
2. **JIT Compilation**: The Arc IR is lowered to LLVM IR and compiled to native machine code using `llvmlite`.
3. **State Management**: All hardware state (registers, active wires) is stored in a single, contiguous byte buffer.
4. **IO View**: A Pythonic interface provides typed access to this buffer, allowing you to read and write signals using native Python types.

## Basic Usage

The easiest way to simulate a module is using the `.simulate()` helper:

```python
from nexhdl import *

class Adder(Module):
    a: INPUT[Logic[8]]
    b: INPUT[Logic[8]]
    out: OUTPUT[Logic[8]]
    
    def build(self, io):
        io.out = io.a + io.b

# Instantiate and simulate
adder = Adder()
with adder.simulate() as sim:
    sim.io.a = 10
    sim.io.b = 20
    sim.step()
    print(f"Result: {sim.io.out}") # Output: 30
```

## Complex Type I/O

The simulator supports NexHDL's rich type system directly. You don't need to manually pack or unpack bits.

### Arrays
Arrays are represented as Python **lists**.

```python
class MyModule(Module):
    arr_in: INPUT[Array[4, Logic[8]]]
    
    def build(self, io):
        ...

with my_module.simulate() as sim:
    # Write list to array
    sim.io.arr_in = [10, 20, 30, 40]
```

### Structs
Structs are represented as Python **dictionaries**.

```python
class Point(Struct):
    x: Logic[16]
    y: Logic[16]

with my_module.simulate() as sim:
    # Write dict to struct
    sim.io.point_in = {'x': 100, 'y': 200}
```


### Nested Types
Combinations work recursively. A `Vector` which is an `Array` of `Point` structs is handled as a list of dictionaries.

```python
# Nested I/O
sim.io.vector_in = [
    {'x': 0, 'y': 0},
    {'x': 10, 'y': 10},
    ...
]
```

## Waveform Tracing (VCD)

You can generate VCD (Value Change Dump) files for debugging in tools like GTKWave. NexHDL automatically flattens complex types into hierarchical signals.

```python
with adder.simulate() as sim:
    sim.vcd("trace.vcd")
    for i in range(10):
        sim.io.a = i
        sim.io.b = i * 2
        sim.step()
```

In your waveform viewer:
- **Structs** appear as scopes containing their fields.
- **Arrays** appear as scopes containing indexed elements like `[0]`, `[1]`, etc.

## Clock & Step Handling

- `sim.step()`: Executes the module evaluation logic once.
- `sim.tick()`: Executes a full clock cycle (falling edge then rising edge) for modules with a clock defined.
- `sim.run(n)`: Executes `n` full clock cycles in a highly optimized machine-code loop. This is significantly faster than calling `tick()` manually in Python for large cycle counts.

## Interacting with Simulation

The simulator object provides direct access to three categories of hardware components:

### 1. I/O Ports (`sim.io`)
Ports defined as `INPUT` or `OUTPUT` in your module are accessed as attributes:
```python
sim.io.clk = 1
sim.io.data_in = 0xDEADBEEF
print(sim.io.data_out)
```

### 2. Internal States (`sim.states`)
Registers can be viewed and edited by their hierarchical string names. This is powerful for verifying internal state without exposing it as a port:
```python
# View or force an internal register value
sim.states["core/alu/reg_a"] = 0xFF
val = sim.states["core/pc/current_pc"]
```

### 3. Memories (`sim.memories`)
Memories are accessed by name to get a `MemoryView`, which behaves like a mutable Python list (supporting slicing and iteration):
```python
# Access memory index 42
sim.memories["ram"][42] = 0xAA

# Bulk initialize memory
sim.memories["ram"][:100] = [0] * 100
```

## Introspection
If you are unsure of the names available in your simulation, you can simply print the containers:
```python
print(sim.io)       # Shows available input and output ports
print(sim.states)   # Shows all internal register paths
print(sim.memories) # Shows all memories and their dimensions (e.g., 65536x32)
```

## Performance Tips

1. **JIT Overhead**: The first call to `.simulate()` can take a fraction of a second as it compiles your module. Subsequent simulation steps are executed at native speed.
2. **Buffer Access**: For massive I/O, remember that Python-to-Hardware conversion happens on every assignment. 
3. **Internal Taps**: Currently, only `INPUT` and `OUTPUT` ports are visible via the `sim.io` interface.
