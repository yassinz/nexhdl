# RISC-V RV32I Example

This directory contains a complete implementation of a **RISC-V (RV32I)** processor core designed with the **NexHDL HDL**. It demonstrates how to build modular hardware components, connect them using buses, and run compiled C/C++ or MicroPython firmware.

## 📂 Project Structure

### Core Components
- **`core.py`**: The top-level module connecting all components.
- **`inst.py`**: Instruction decoding and immediate extraction logic.
- **`alu.py`**: Arithmetic Logic Unit for math, logic, and branch comparison.
- **`reg_file.py`**: 32-register filing system.
- **`lsu.py`**: Load/Store Unit and unified RAM memory.
- **`pc.py`**: Program Counter management with branch/jump logic.
- **`csr.py`**: Control and Status Registers (cycles, time).

### Firmware & Tools
- **`console.py`**: A GUI terminal (Tkinter) to interact with the processor via MMIO.
- **`program/`**: Contains a C firmware project.
  - `main.c`: Firmware source code (tests hex dumps, CSRs, and I/O).
  - `Makefile`: Build script for the RISC-V toolchain.
  - `core.ld`: Custom linker script mapping memory layout.

## 🚀 How to Run

### 1. Run Individual Unit Tests
Each component file (`alu.py`, `lsu.py`, etc.) contains its own test suite. You can run them directly to verify functionality:
```bash
python examples/RV32I/alu.py
python examples/RV32I/lsu.py
```

### 2. Run the Full Core Simulation
To run the full processor executing the pre-compiled firmware:
```bash
python examples/RV32I/core.py
```
This will simulate the processor stepping through `program/program.bin` and print MMIO output to your terminal.

### 3. Run the Interactive Console
If you have a GUI environment, you can run the interactive terminal:
```bash
python examples/RV32I/console.py
```

## 🛠 Building Firmware
To modify and rebuild the C firmware, you need the RISC-V GCC toolchain (`riscv-none-elf-gcc`):
```bash
cd examples/RV32I/program
make
```

## 📝 MMIO Configuration
The core includes a simple Memory-Mapped I/O (MMIO) interface:
- **Address `0x110000`**: Writing to this address sends a character to the console. Reading from it catches keyboard input (blocking in the console GUI).
