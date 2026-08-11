# Parameterization

NexHDL supports powerful parameterization using Python's PEP 695 generic syntax.

## Generic Modules

Define modules with type or value parameters:

```python
class Adder[WIDTH](Module):
    a: INPUT[Logic[WIDTH]]
    b: INPUT[Logic[WIDTH]]
    out: OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        io.out = io.a + io.b

# Use with different widths
adder8 = Adder[8]()
adder16 = Adder[16]()
adder32 = Adder[32]()
```

### Multiple Parameters

```python
class FIFO[DEPTH, WIDTH](Module):
    clk: INPUT[Clock]
    push: INPUT[Logic[1]]
    pop: INPUT[Logic[1]]
    data_in: INPUT[Logic[WIDTH]]
    data_out: OUTPUT[Logic[WIDTH]]
    full: OUTPUT[Logic[1]]
    empty: OUTPUT[Logic[1]]
    
    def build(self, io):
        # Use DEPTH and WIDTH
        memory = Reg[Array[DEPTH, Logic[WIDTH]]]()
        # ... implementation

# Instantiate
fifo = FIFO[16, 32]()  # 16 deep, 32-bit wide
```

## Generic Structs

Parameterize composite types:

```python
class Point[WIDTH](Struct):
    x: Logic[WIDTH]
    y: Logic[WIDTH]

# Use
p8 = Point[8](x=10, y=20)
p16 = Point[16](x=100, y=200)
p32 = Point[32](x=1000, y=2000)
```

### With Methods

```python
class Vector[WIDTH](Struct):
    x: Logic[WIDTH]
    y: Logic[WIDTH]
    
    def __add__(self, other):
        return Vector[WIDTH](
            x=self.x + other.x,
            y=self.y + other.y
        )
    
    def magnitude_squared(self):
        return self.x * self.x + self.y * self.y

# Use
v1 = Vector[16](x=3, y=4)
v2 = Vector[16](x=1, y=2)
v3 = v1 + v2  # Vector[16](x=4, y=6)
```

## Parameter Arithmetic

Perform operations on parameters:

```python
class DoubleWidth[N](Module):
    in_data: INPUT[Logic[N]]
    out_data: OUTPUT[Logic[N * 2]]  # Double width
    
    def build(self, io):
        io.out_data = io.in_data.zext(N * 2)

class IndexedMemory[SIZE](Module):
    addr: INPUT[Logic[clog2(SIZE)]]  # Address width
    data: OUTPUT[Logic[32]]
    
    def build(self, io):
        mem = Array[SIZE, Logic[32]]()
        io.data = mem[io.addr]
```

### Available Operations

```python
# Arithmetic
N * 2
N + 1
N - 1
N / 2

# Utility functions
clog2(N)  # Ceiling log2
```

## Type Parameters

Pass types as parameters:

```python
class Register[T](Module):
    clk: INPUT[Clock]
    data_in: INPUT[T]
    data_out: OUTPUT[T]
    
    def build(self, io):
        reg = Reg[T]()
        with io.clk.posedge:
            reg.next = io.data_in
        io.data_out = reg

# Use with different types
reg_logic = Register[Logic[32]]()
reg_array = Register[Array[8, Logic[16]]]()
reg_struct = Register[Point]()
```

## Nested Parameterization

Parameters resolve through multiple levels:

```python
class Matrix[ROWS, COLS, WIDTH](Struct):
    data: Array[ROWS, Array[COLS, Logic[WIDTH]]]

class MatrixProcessor[ROWS, COLS, WIDTH](Module):
    clk: INPUT[Clock]
    matrix_in: INPUT[Matrix[ROWS, COLS, WIDTH]]
    matrix_out: OUTPUT[Matrix[ROWS, COLS, WIDTH]]
    
    def build(self, io):
        reg = Reg[Matrix[ROWS, COLS, WIDTH]]()
        with io.clk.posedge:
            reg.next = io.matrix_in
        io.matrix_out = reg

# Use
processor = MatrixProcessor[4, 4, 16]()
```

## Conditional Logic with Parameters

```python
class ConfigurableALU[WIDTH, HAS_MUL](Module):
    a: INPUT[Logic[WIDTH]]
    b: INPUT[Logic[WIDTH]]
    op: INPUT[Logic[2]]
    out: OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        add = io.a + io.b
        sub = io.a - io.b
        
        if HAS_MUL:
            mul = io.a * io.b
            io.out = Mux[Logic[WIDTH]](
                io.op[0],
                Mux[Logic[WIDTH]](io.op[1], mul, sub),
                add
            )
        else:
            io.out = Mux[Logic[WIDTH]](io.op[0], sub, add)

# Different configurations
alu_simple = ConfigurableALU[32, False]()
alu_full = ConfigurableALU[32, True]()
```

## Best Practices

### 1. Meaningful Parameter Names

```python
# Good
class FIFO[DEPTH, DATA_WIDTH](Module): ...

# Bad
class FIFO[N, W](Module): ...
```

### 2. Document Parameter Constraints

```python
class Cache[LINE_SIZE, NUM_LINES](Module):
    """
    Simple cache implementation.
    
    Parameters:
        LINE_SIZE: Bytes per cache line (must be power of 2)
        NUM_LINES: Number of cache lines (must be power of 2)
    """
```

### 3. Provide Sensible Defaults

```python
# Use common configurations
StandardFIFO = FIFO[16, 32]
DeepFIFO = FIFO[256, 32]
WideFIFO = FIFO[16, 128]
```

### 4. Parameter Validation with `Param`

For more advanced and declarative validation, use the `Param` class. This allows you to enforce type and value constraints directly in the class definition.

Validation occurs in two steps:
1. **Base Type Check**: Ensures the parameter is an instance of the specified type (e.g., `int`).
2. **Logic Check**: Executes a custom predicate (lambda) to validate the value.

```python
from nexhdl import Module, Logic, Array, INPUT, Param

# 1. Define reusable validators
PositiveInt = Param[int](lambda x: x > 0, "Must be positive")
PowerOfTwo  = Param[int](lambda x: x > 0 and (x & (x - 1)) == 0, "Must be a power of two")

# 2. Use as bounds in the generic definition
class DSP[SIZE: PowerOfTwo, WIDTH: PositiveInt](Module):
    x: INPUT[Array[SIZE, Logic[WIDTH]]]
    y: INPUT[Array[SIZE, Logic[WIDTH]]]
    
    def build(self, io):
        # Implementation...
        pass

# 3. Specialization triggers validation
dsp1 = DSP[16, 32]   # Success
dsp2 = DSP[15, 32]   # Raises ValueError: Must be a power of two
dsp3 = DSP["16", 32] # Raises TypeError: Parameter 'SIZE' must be int
```

This approach is cleaner than manual `__init__` checks because it catches errors at the moment of specialization (e.g., when writing `DSP[15, 32]`), rather than waiting for instantiation.

```python
# Validation works for Structs too

EvenValue = Param[int](lambda x: x % 2 == 0, "Must be even")

class EvenPoint[VAL: EvenValue](Struct):
    x: Logic[VAL]
    y: Logic[VAL]

p = EvenPoint[8]  # Success
p = EvenPoint[7]  # Raises ValueError: Must be even
```
