# NexHDL HDL: AI Developer Reference

This document is a comprehensive technical reference for AI agents to design, implement, and simulate hardware components using the NexHDL HDL library.

---

## 🏗️ 1. Core Module Architecture

All hardware components are classes inheriting from `Module`.

### **Structural Rules**
1.  **Port Definitions**: Defined as class-level type annotations.
    - `INPUT[Type]`, `OUTPUT[Type]`.
2.  **The `build` Method**: The logic **MUST** reside inside `def build(self, io):`.
    - **No logic** should be in `__init__` except for simple scalar parameter checks.
3.  **IO Object**: Access all ports via the `io` argument.
    - Read inputs: `a = io.a`.
    - Write outputs (exactly once): `io.out = result`.
4.  **Instantiations**: Submodules are created inside `build`.
    - `sub = SubModule[Params](port_a=io.in_a, port_b=some_internal_wire)`.
    - Access submodule outputs: `io.final_out = sub.out_port`.

---

## 💎 2. Unified Type System

NexHDL types are fully composable (e.g., `Array[16, PointStruct]`).

### **Logic (Bit Vectors)**
- **Type**: `Logic[N]`
- **Indexing**: **Index 0 is the Least Significant Bit (LSB)**.
- **Slicing**: Standard Python `[low:high]` (e.g., `val[0:4]` extracts bits 0, 1, 2, 3).
- **Python Interop**: Native `int` can be used in expressions. They are auto-converted to hardware constants if they fit the bit-width.
- **Rules**: Binary operations (arithmetic/bitwise) require **identical bit-widths**. Use `.zext()` or `.trunc()` to align them.

### **Composite Types**
- **`Array[SIZE, TYPE]`**: Fixed-size homogeneous collection.
  - **Bit Layout**: **Big-Endian (MSB-first)**. `arr[0]` is at the **Most Significant Bits** (MSB).
  - **Access**: `arr[0]` (static) or `arr[Logic[N](idx)]` (dynamic).
  - **Slicing**: `arr[0:2]` returns a slice of elements.
- **`Struct`**: Named fields.
  - **Bit Layout**: **Big-Endian (MSB-first)**. The **first** defined field occupies the **Most Significant Bits**.
  - **Casting**: Structs can be bit-cast to `Logic` and vice-versa if widths match.
  - **Operator Overloading**: You can define magic methods like `__add__`, `__sub__`, etc., to enable arithmetic on high-level types.
    ```python
    class Point[W: int](Struct):
        x: Logic[W]; y: Logic[W]
        def __add__(self, other):
            return Point[W](x=self.x + other.x, y=self.y + other.y)
    ```
- **`Union`**: Multiple views of the same bit storage. `width = max(field_widths)`.

---

## ⚙️ 3. Hardware Primitives

### **Stateful Elements**
1.  **`Reg[Type](init=None)`**:
    - Acts like its underlying value in expressions (IS-A relationship).
    - Assignment: `reg.next = val` (must be inside a clock context).
2.  **`Wire[Type]()`**: For forward declarations or circular logic.
    - Assignment: `wire.assign = val`.
3.  **`Mem[SIZE, Type]()`**: Fixed-size memory array.
    - **Usage**: Must be inside a clock context.
    - **Read**: `val = mem[addr]` or `val = mem.read(addr, en)`.
    - **Write**: `mem.write(addr, data, en)`.
4.  **`Fifo[DEPTH, Type](almost_full=X, almost_empty=Y)`**:
    - **Ops**: `fifo.push(data, en)`, `val = fifo.pop(en)`.
    - **Flags**: `fifo.full`, `fifo.empty`, `fifo.almost_full`, `fifo.almost_empty`.

### **Functional Logic**
5.  **`Mux[Type](cond, true_val, false_val)`**: Type-safe multiplexer.
6.  **`Map[K_WIDTH, V_Type]((key, val), ..., default=X)`**: Priority-based LUT.

---

## 🚦 4. Elaboration vs. Hardware Logic (CRITICAL)

AI developers must distinguish between **Elaboration-time** Python and **Runtime** Hardware logic.

### **Python `if` is NOT Hardware**
- **WRONG**: `if io.cond: io.out = a` 
  - Python `if`/`and`/`or`/`not` operate on Python truthiness rather than hardware signals and raise `TypeError("Use Mux/&/| for hardware conditions")` on `NexValue` signals.
- **RIGHT**: `io.out = Mux[Logic[N]](io.cond, a, b)`
  - This generates a hardware multiplexer gates.

### **Rules for `if` statements**
1.  **Use `if` for Elaboration**: Configuring hardware structure based on **Parameters**.
    ```python
    if USE_MULTIPLIER:
        io.out = io.a * io.b
    else:
        io.out = io.a + io.b
    ```
2.  **Use `Mux`/`Map` for Signals**: Selecting values based on **Hardware Inputs**.
    ```python
    # Select result based on a 1-bit signal
    io.out = Mux[Logic[32]](io.sel, val_a, val_b)
    ```

---

## ⚡ 5. Clock Contexts & Sequential Logic

Sequential updates **MUST** be wrapped in a `with` context.

```python
with io.clk.posedge, io.rst.negedge:
    reg.next = counter + 1
    fifo.push(io.data, io.valid)
```
- Supported: `.posedge`, `.negedge`.
- Clock contexts implicitly handle `Mem` and `Fifo` control signals.

---

## 6. Bit Manipulation & Arithmetic

### **Operators**
- **Math**: `+`, `-`, `*`, `/`, `%`.
- **Bitwise**: `&`, `|`, `^`, `~`, `<<`, `>>`.
- **Concatenation**: `@` (e.g., `high @ low`).
- **Reduction**: `.parity()`.

### **Signed Logic**
- Use `.si` to view a `Logic` value as signed: `result = a.si + b.si`.

### **Width Management**
- **`.zext(W)`** / **`.sext(W)`**: Zero/Sign extend to width `W`.
- **`.trunc(W)`**: Truncate to width `W`.
- **`.replicate(N)`**: Repeat bitvector `N` times.
- **`.reverse()`**: Reverse all bits.

---

## 🛠️ 7. Hardware vs. Python Operators (CRITICAL)

LLMs often confuse Elaboration-time (Python) operators with Runtime (Hardware) operators.

| Operation | Python (Elaboration) | NexHDL (Hardware) |
| :--- | :--- | :--- |
| **Logic** | `if`, `and`, `or`, `not` | `Mux`, `Map`, `&`, `|`, `~` |
| **Comparison** | Use in `if` for params | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| **Arithmetic** | For calculating widths | `+`, `-`, `*`, `/`, `%` |

**Rule**: If you are using `and`, `or`, or `not` on anything coming from `io` or `Reg`, you are making a **SYNTAX ERROR**. Use `&`, `|`, and `~` instead.

---

## 🔄 8. Type Casting Syntax

You can cast between `Logic`, `Struct`, and `Array` as long as the total bit-width matches exactly.

```python
# 1. Any type to Logic (Flattening)
bits = Logic[32](my_struct)
bits = Logic[32](my_array)

# 2. Logic to Struct/Array (Unflattening)
my_struct = MyStruct(io.bits)
my_array  = Array[4, Logic[8]](io.bits)

# 3. Array to Struct (Protocol Decoding)
# Both Array and Struct are Big-Endian (MSB-first), so they align!
# If payload is Array[N, Logic[8]], it can be cast directly.
header = IPv4Header(io.payload) 
```

---

## 🌀 9. Hardware Generation (Spatial vs. Temporal)

Python loops are for **generating parallel hardware** (Spatial), not for sequential time (Temporal).

```python
def build(self, io):
    # SPATIAL: This generates 4 physical adders in parallel
    results = [io.a[i] + io.b[i] for i in range(4)]
    
    # TEMPORAL: This updates a register over clock cycles
    with io.clk.posedge:
        reg.next = reg + 1
```

---

## ⚡ 10. Clock Contexts & Sequential Logic

Sequential updates **MUST** be wrapped in a `with` context.

```python
with io.clk.posedge, io.rst.negedge:
    reg.next = counter + 1
    fifo.push(io.data, io.valid)
```
- Supported: `.posedge`, `.negedge`.
- Clock contexts implicitly handle `Mem` and `Fifo` control signals.

---

## 🧩 11. Parameterization & Validators

Use generics for reusable components. Use `Param` for strict hardware constraints.

```python
PowerOf2 = Param[int](lambda x: x > 0 and (x & (x - 1)) == 0, "Must be power of 2")

class Buffer[DEPTH: PowerOf2, WIDTH: int](Module):
    data: INPUT[Array[DEPTH, Logic[WIDTH]]]
    ...
```

---

## 🧪 12. Simulation & Verification

- **Format**: `Logic` -> `int`, `Array` -> `list`, `Struct` -> `dict`.
- **Latency**: Remember that `Reg` introduces a 1-cycle delay.
- **VCD**: Use `sim.vcd("trace.vcd")` to debug hierarchy.
- **Optimized Simulation**: Use `sim.run(N)` for high-speed multi-cycle execution.

---

## 🏆 13. Master Template (The Golden Standard)

```python
from nexhdl import *

class MasterExample[WIDTH: int](Module):
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    en:     INPUT[Logic[1]]
    data_a: INPUT[Array[4, Logic[WIDTH]]]
    data_b: INPUT[Array[4, Logic[WIDTH]]]
    out:    OUTPUT[Array[4, Logic[WIDTH]]]

    def build(self, io):
        # 1. State: Register an array of values
        storage = Reg[Array[4, Logic[WIDTH]]]()
        
        # 2. Spatial Generation: Parallel logic using Python list
        # Note: Using & (hardware AND), not 'and' (Python)
        comp = [Mux[Logic[WIDTH]](io.en, io.data_a[i] + io.data_b[i], io.data_a[i]) 
                for i in range(4)]
        
        # 3. Temporal Logic: Clocked update
        with io.clk.posedge, io.rst.negedge:
            storage.next = Array[4, Logic[WIDTH]](comp)
            
        io.out = storage

if __name__ == "__main__":
    dut = MasterExample[16]()
    with dut.simulate() as sim:
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        sim.io.en = 1
        sim.io.data_a = [10, 20, 30, 40]
        sim.io.data_b = [1, 2, 3, 4]
        sim.tick() # Data moves to 'storage' register
        print(sim.io.out) # [11, 22, 33, 44]
```

---

## 📜 14. AI Design Checklist
- [ ] **Import**: Used `from nexhdl import *`?
- [ ] **Build**: All logic inside `def build(self, io):`?
- [ ] **Operators**: Used `&`, `|`, `~` for signals (not `and`, `or`, `not`)?
- [ ] **Conditionals**: Used `Mux` or `Map` for signal-based branching?
- [ ] **Widths**: Used `.zext()/.sext()` or `.trunc()` to match binary operand widths?
- [ ] **Address**: Used `clog2(SIZE)` for memory addresses?
- [ ] **Registers**: Assigned via `.next` inside a `with clk.posedge` context?
