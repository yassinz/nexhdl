# NexHDL HDL

A modern, Python-based Hardware Description Language (HDL) that compiles to SystemVerilog via CIRCT.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **🎯 Type-Safe**: Strong typing with `Logic`, `Array`, `Struct`, and `Union`
- **🔧 Composable**: Types compose infinitely - `Reg[Array[4, Struct]]` just works
- **🐍 Pythonic**: Modern Python with PEP 695 generics - `class Adder[WIDTH](Module)`
- **⚡ Fast**: CIRCT backend for rapid compilation
- **🔬 Simulation**: Built-in LLVM-based simulator with VCD output
- **📦 Clean**: Predictable mapping to SystemVerilog

## Quick Start

### Installation

```bash
pip install nexhdl
```

### Hello World - Counter

```python
from nexhdl import *

class Counter(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    out: OUTPUT[Logic[32]]

    def build(self, io):
        count = Reg[Logic[32]]()
        
        with io.clk.posedge, io.rst.negedge:
            count.next = count + 1
            
        io.out = count

# Generate Mlir and Verilog
counter = Counter()
print(counter.mlir())
print(counter.verilog())

# Simulate
with counter.simulate() as sim:
    print(sim.llvm_ir())
    print(sim.machine_asm())
    sim.io.rst = 0
    sim.tick()
    sim.io.rst = 1
    for i in range(10):
        sim.tick()
        print(f"count = {sim.io.out}")

```

### Parameterized Design

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
```

### Using Structs

```python
class Point[WIDTH](Struct):
    x: Logic[WIDTH]
    y: Logic[WIDTH]

    def __add__(self, other):
        return Point[WIDTH](
            x=self.x + other.x,
            y=self.y + other.y
        )

class PointAdder[WIDTH](Module):
    a: INPUT[Point[WIDTH]]
    b: INPUT[Point[WIDTH]]
    out: OUTPUT[Point[WIDTH]]
    
    def build(self, io):
        io.out = io.a + io.b

addr = PointAdder[8]()
print(addr.verilog())     
```

## Core Concepts

### Types

- **Logic[N]** - N-bit vectors with full arithmetic/bitwise operations
- **Array[N, T]** - Fixed-size arrays of any type
- **Struct** - Composite types with named fields
- **Union** - Tagged unions for multiple views of data

### Primitives

- **Reg[T]** - Registers with `.next` assignment
- **Wire[T]** - Forward-declared wires with `.assign` property
- **Mux[T]** - Type-safe multiplexers
- **Map[W, T]** - Combinational lookup tables
- **Mem[N, T]** - Synchronous memories with `.read` and `.write` methods
- **Fifo[N, T]** - FIFO with `.push` and `.pop` methods


### Interfaces & Streams (ESI-Style)

- **Stream[T]** - Ready/valid streaming channels with automatic direction handling
- **Interface / Bundle** - Custom protocol and bus groupings with `INPUT[...]` and `OUTPUT[...]` polarity flipping
- **StreamChannel[T]** - Internal point-to-point streaming channel wiring

```python
class StreamProcessor[WIDTH: int](Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    inp: INPUT[Stream[Logic[WIDTH]]]
    out: OUTPUT[Stream[Logic[WIDTH]]]

    def build(self, io):
        io.inp.ready = io.out.ready
        io.out.push(io.inp.data * 2, enable=io.inp.valid)
```

### Registers

```python
# Create register
reg = Reg[Logic[32]]()

# With initial value
reg = Reg[Logic[32]](init=42)

# Assign in clock context
with io.clk.posedge:
    reg.next = reg + 1
```

### Wires

```python
# Create wire
w = Wire[Logic[32]]()

# Use before assignment
io.out = w

# Assign later
w.assign = io.a + io.b
```

### Multiplexers

```python
result = Mux[Logic[32]](sel, true_val, false_val)
```

## Examples

See the `examples/` directory for a variety of hardware designs:
- **[RV32I](examples/RV32I/)**: A complete RISC-V RV32I CPU implementation.
- **[Streaming Pipeline](examples/stream_pipeline.py)**: Elastic packet processing with `Stream[Packet]` and backpressure.
- **[DSP Components](examples/dsp.py)**: DotProduct, Pipelined MAC, and FIR filters.
- **[Networking](examples/crc32.py)**: CRC-32 generator and packet protocol inspectors.
- **[Systolic Array](examples/systolic_array.py)**: Parallel matrix multiplication engine.
- **[Basics](examples/alu.py)**: ALU, state machines, counters, and logic gates.

## Documentation

- [Types](docs/types.md) - Logic, Array, Struct, Union
- [Primitives](docs/primitives.md) - Reg, Wire, Mux, Mem, Fifo
- [Interfaces & Streams](docs/interfaces.md) - Interface, Bundle, Stream (ESI)
- [Modules](docs/modules.md) - Module definition and hierarchy
- [Parameterization](docs/parameterization.md) - Generic types and modules
- [Simulation](docs/simulation.md) - Fast JIT-based simulation and VCD tracing

## Project Structure

```
nexhdl/
├── nexhdl/
│   ├── core/           # Module system
│   ├── types/          # Type system (Logic, Array, Struct, Union)
│   ├── primitives/     # Reg, Wire, Mux, Mem, Fifo, Map
│   ├── interfaces/     # Interface, Bundle, Stream (ESI)
│   ├── simulation/     # LLVM-based simulator
│   └── parameters/     # PEP 695 generics & parameter resolvers
├── examples/           # Example designs
├── test/               # Tests
├── docs/               # Documentation
└── README.md
```

## Requirements

- Python 3.13+
- CIRCT (installed via pip)
- llvmlite

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
python -m pytest test/

# Run specific test
python test/test_reg.py
```

## Design Philosophy

1. **Types compose infinitely** - Any type can contain any other type
2. **Python-first** - Use Python's features, don't fight them
3. **Predictable output** - Clear mapping to SystemVerilog
4. **Fast compilation** - CIRCT backend for speed
5. **Type safety** - Catch errors at compile time, not simulation

## Status

⚠️ **Alpha** - Work in progress. API may change.

Current focus:
- Core type system ✅
- Module system ✅
- Primitives (Reg, Wire, Mux, Map, Mem, Fifo) ✅
- Interfaces and Streams (ESI) ✅
- Simulation ✅
- Documentation 🚧
- Fsm and Pipeline 🚧
- Standard library 🚧

## Contributing

Contributions welcome! Areas of interest:
- Documentation improvements
- Bug reports and fixes
- Example designs

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- Built on [CIRCT](https://circt.llvm.org/) - Circuit IR Compilers and Tools
- Inspired by [Chisel](https://www.chisel-lang.org/), [Amaranth](https://amaranth-lang.org/), and [MyHDL](http://www.myhdl.org/)

## Contact

For questions, issues, or discussions, please open an issue on GitHub.

---

**Note**: This is a research/educational project. For production use, consider mature alternatives.
