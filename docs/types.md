# Data Types

NexHDL provides a rich, composable type system.

## Logic

`Logic[width]` represents a bit vector of a specific width.

### Creation

```python
# Type
Logic[8]        # 8-bit type
Logic[32]       # 32-bit type

# Value
val = Logic[8](42)          # From int
val = Logic[8](ir_value)    # From CIRCT value
val = Logic[8]()            # Zero
```

### Operations

```python
# Arithmetic
a + b, a - b, a * b, a / b, a % b

# Bitwise
a & b, a | b, a ^ b, ~a
a << b, a >> b

# Comparison
a == b, a != b, a < b, a <= b, a > b, a >= b

# Indexing
val[0]          # Single bit
val[4:7]        # Bit range
val[0:3]        # Lower nibble

# Concatenation
high @ low      # Concatenate bits

# Extension
val.zext(16)    # Zero extend to 16 bits
val.sext(16)    # Sign extend to 16 bits
val.trunc(4)    # Truncate to 4 bits

val.replicate(2)   # Replicate the value 2 times
val.reverse()      # Reverse the bits
```

### Interoperability with Python

You can use native Python integers directly in expressions with `Logic` values. NexHDL automatically converts them to hardware constants, provided the integer fits within the width of the `Logic` operand.

```python
a = Logic[8](10)
b = a + 5        # Valid: 5 is converted to Logic[8]
c = a & 0xFF     # Valid: fits in 8 bits
d = a | 0xFFFF   # Error: value out of range for Logic[8]
```

### Bit-Width Consistency

Hardware operations (arithmetic, bitwise, comparison) require that both operands have the **exact same bit-width**. 

```python
a = Logic[8](1)
b = Logic[16](2)
c = a + b        # Error: Width mismatch (8 vs 16)

# Use extension/truncation to align widths
c = a.zext(16) + b # Valid
```

### Signed Arithmetic

```python
a = Logic[8](250)
b = Logic[8](10)

# Unsigned (default)
result = a + b  # 4 (wraps)

# Signed
result = a.si + b.si  # -6 (treats as signed)
```

## Array

`Array[size, element_type]` represents a fixed-size collection.

### Creation

```python
# Type
Array[4, Logic[8]]              # 4 bytes
Array[16, Logic[32]]            # 16 words
Array[8, Array[8, Logic[8]]]    # 8x8 matrix

# Value
arr = Array[4, Logic[8]]([0xAA, 0xBB, 0xCC, 0xDD])
arr = Array[4, Logic[8]]()      # Zero-initialized
```

### Operations

```python
# Indexing
val = arr[0]            # Static index
val = arr[Logic[2](i)]  # Dynamic index

# Assignment
arr[0] = Logic[8](0xFF)

# Slicing
sub = arr[0:2]   # Elements [0:2]

# Concatenation
big = Array.concat(arr1, arr2, arr3)

# Iteration
for elem in arr:
    # Process each element
    pass
```

### Nested Arrays

```python
# 2D array
matrix = Array[8, Array[8, Logic[16]]]()

# Access
val = matrix[row][col]

# Assignment
matrix[row][col] = Logic[16](42)
```

## Struct

`Struct` allows defining composite types with named fields.

### Definition

```python
class Point(Struct):
    x: Logic[32]
    y: Logic[32]

class Packet(Struct):
    header: Logic[16]
    data: Array[64, Logic[8]]
    valid: Logic[1]
```

### Creation

```python
# From fields
p = Point(x=Logic[32](10), y=Logic[32](20))

# From ints (auto-converted)
p = Point(x=10, y=20)

# Zero-initialized
p = Point()

# From CIRCT value
p = Point(ir_value)
```

### Access

```python
# Read fields
x_val = p.x
y_val = p.y

# Fields are properly typed
io.out = p.x + p.y  # Works!
```

### Parameterized Structs

```python
class Point[WIDTH](Struct):
    x: Logic[WIDTH]
    y: Logic[WIDTH]

# Use with different widths
p16 = Point[16](x=10, y=20)
p32 = Point[32](x=100, y=200)

# In arrays
points = Array[4, Point[16]]()
```

### Methods

```python
class Point[WIDTH](Struct):
    x: Logic[WIDTH]
    y: Logic[WIDTH]
    
    def __add__(self, other):
        return Point[WIDTH](
            x=self.x + other.x,
            y=self.y + other.y
        )

# Use
p1 = Point[16](x=10, y=20)
p2 = Point[16](x=5, y=15)
p3 = p1 + p2  # Point[16](x=15, y=35)
```

## Union

`Union` represents a tagged union (multiple views of same data).

### Definition

```python
class Instruction(Union):
    raw: Logic[32]
    r_type: RType
    i_type: IType
    s_type: SType
```

### Usage

```python
inst = Instruction(raw=Logic[32](0x12345678))

# Access different views
opcode = inst.r_type.opcode
imm = inst.i_type.immediate
```

### Key Points

- Stored as `Logic[max_width]`
- All fields share same storage
- Useful for instruction decoding
- No runtime overhead

## Clock and Reset

Special types for sequential logic.

```python
class Counter(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    out: OUTPUT[Logic[32]]
    
    def build(self, io):
        count = Reg[Logic[32]]()
        
        # Clock context
        with io.clk.posedge:
            count.next = count + 1
        
        # With reset
        with io.clk.posedge, io.rst.negedge:
            count.next = count + 1
        
        io.out = count
```

## Type Composition

Types compose infinitely:

```python
# Array of structs
Array[16, Point]

# Struct with arrays
class CacheLine(Struct):
    valid: Logic[1]
    tag: Logic[24]
    data: Array[64, Logic[8]]

# Array of array of structs
Array[4, Array[8, Point]]

# Nested structs
class BoundingBox(Struct):
    top_left: Point
    bottom_right: Point

# In registers
Reg[Array[4, Point]]()
Reg[CacheLine]()

# In wires
Wire[Array[16, CacheLine]]()
```

## Packing and Indexing

NexHDL types have deterministic bit-level representations, ensuring compatibility with SystemVerilog and external IP.

### Array Packing & Simulation

Arrays are packed **Big-Endian** (MSB-first) with respect to their indices. This ensures consistent alignment with `Struct` fields, enabling direct bit-casting between arrays of bytes and network protocol headers.

- **Bit Layout**: `arr[0]` resides at the **Most Significant Bits** (MSB) of the bitstream.
- **Simulation I/O**: Lists used for simulation inputs or outputs follow the natural Python order: `list[0]` maps to `arr[0]`.

Example:
```python
# Create array
arr = Array[3, Logic[8]]([0xAA, 0xBB, 0xCC])

# Bit-level representation (viewed as a single bit-vector):
# [ 0xAA (MSB/Index0) | 0xBB (Index1) | 0xCC (LSB/Index2) ]

# Simulation access:
sim.io.data = [0xAA, 0xBB, 0xCC]
assert sim.io.data[0] == 0xAA
```

This convention makes cross-type conversions (like casting an `Array[4, Logic[8]]` to a 32-bit `Logic` or a 4-field `Struct`) intuitive and predictable.

### Struct Packing

Structs are packed **Big-Endian** (MSB-first) with respect to their field definitions.
- The **first field** defined in the class resides at the **Most Significant Bits**.
- The **last field** resides at the **Least Significant Bits**.

```python
class Header(Struct):
    version: Logic[4]  # Bits [11:8]
    length:  Logic[8]  # Bits [7:0]
```

### Real-World Example: RISC-V R-Type

A common use for structs is decoding hardware protocols or instructions. A RISC-V R-type instruction is defined with the following bit fields: `funct7[31:25]`, `rs2[24:20]`, `rs1[19:15]`, `funct3[14:12]`, `rd[11:7]`, `opcode[6:0]`.

```python
class RType(Struct):
    # Standard field order: MSB to LSB
    funct7: Logic[7]   # [31:25]
    rs2:    Logic[5]   # [24:20]
    rs1:    Logic[5]   # [19:15]
    funct3: Logic[3]   # [14:12]
    rd:     Logic[5]   # [11:7]
    opcode: Logic[7]   # [6:0]

# Cast a 32-bit register to the struct
inst = Logic[32](0x00b50533) # add a0, a0, a1
decode = RType(inst)

# Access fields directly
rd_idx = decode.rd      # Returns 5-bit Logic value
op = decode.opcode      # Returns 7-bit Logic value
```

This ensures that bit-casting a struct to a logic vector maintains the visual order of fields as they would appear in a protocol specification.

### Summary Table

| Type | Order | Index 0 / Field 1 Position |
| :--- | :--- | :--- |
| **Logic** | Little-Endian | LSB |
| **Array** | Big-Endian | MSB |
| **Struct** | Big-Endian | MSB |

---

## Type Utilities

```python
# Get type from value
val_type = val.type_like()

# Create value of same type
new_val = val.type_like()(42)

# Zero value
zero = MyType.zero()
```
