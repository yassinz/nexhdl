#!/usr/bin/env python3
"""
Test file for Mem primitive.
"""

from nexhdl import *


class MemTestSimple[SIZE, WIDTH](Module):
    """Simple memory test module."""
    clk:  INPUT[Clock]
    rst:  INPUT[Reset]
    we:   INPUT[Logic[1]]
    re:   INPUT[Logic[1]]
    addr: INPUT[Logic[clog2(SIZE)]]
    data: INPUT[Logic[WIDTH]]
    out:  OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        # Create memory
        mem = Mem[SIZE, Logic[WIDTH]]()
        
        # Write in clock context
        with io.clk.posedge, io.rst.negedge:
            # Read (index syntax)
            io.out = mem[io.addr]
            # Write
            mem.write(io.addr, io.data, io.we)


class Point(Struct):
    """Simple struct for testing."""
    x: Logic[16]
    y: Logic[16]


class MemTestStruct(Module):
    """Test memory with Struct type."""
    clk:  INPUT[Clock]
    rst:  INPUT[Reset]
    we:   INPUT[Logic[1]]
    addr: INPUT[Logic[4]]  # 16 entries
    x_in: INPUT[Logic[16]]
    y_in: INPUT[Logic[16]]
    x_out: OUTPUT[Logic[16]]
    y_out: OUTPUT[Logic[16]]
    
    def build(self, io):
        # Memory of Point structs
        mem = Mem[16, Point]()
        
        
        # Write in clock context
        with io.clk.posedge, io.rst.negedge:
            point = mem[io.addr]
            io.x_out = point.x
            io.y_out = point.y
            
            new_point = Point(x=io.x_in, y=io.y_in)
            mem.write(io.addr, new_point, io.we)


class MemTestArray(Module):
    """Test memory with Array type."""
    clk:  INPUT[Clock]
    rst:  INPUT[Reset]
    we:   INPUT[Logic[1]]
    addr: INPUT[Logic[3]]  # 8 entries
    data: INPUT[Array[4, Logic[8]]]
    out:  OUTPUT[Array[4, Logic[8]]]
    
    def build(self, io):
        # Memory of arrays
        mem = Mem[8, Array[4, Logic[8]]]()
        
        with io.clk.posedge, io.rst.negedge:
            # Read
            io.out = mem[io.addr]
            # Write
            mem.write(io.addr, io.data, io.we)


class MemoryByteEnable[SIZE](Module):
    """Memory with byte enable."""
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    we:       INPUT[Logic[4]]
    waddr:    INPUT[Logic[clog2(SIZE)]]
    raddr:    INPUT[Logic[clog2(SIZE)]]
    data:     INPUT[Logic[32]]

    out:      OUTPUT[Logic[32]]

    def build(self, io):
        mem0 = Mem[SIZE, 8]()
        mem1 = Mem[SIZE, 8]()
        mem2 = Mem[SIZE, 8]()
        mem3 = Mem[SIZE, 8]()

        with io.clk.posedge, io.rst.negedge:
            mem0.write(io.waddr, io.data[0:8],   io.we[0])
            mem1.write(io.waddr, io.data[8:16],  io.we[1])
            mem2.write(io.waddr, io.data[16:24], io.we[2])
            mem3.write(io.waddr, io.data[24:32], io.we[3])
            
        io.out = mem3[io.raddr] @ mem2[io.raddr] @ mem1[io.raddr] @ mem0[io.raddr]


class SimpleDualPortMem[SIZE: int, WIDTH: int](Module):
    """Simple dual-port memory."""
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    we:     INPUT[Logic[1]]
    data:   INPUT[Logic[WIDTH]]
    waddr:  INPUT[Logic[clog2(SIZE)]]
    raddr0: INPUT[Logic[clog2(SIZE)]]
    raddr1: INPUT[Logic[clog2(SIZE)]]

    rs1 : OUTPUT[Logic[WIDTH]]
    rs2 : OUTPUT[Logic[WIDTH]]

    def build(self, io):
        mem = Mem[SIZE, WIDTH]()

        with io.clk.posedge, io.rst.negedge:
            mem.write(io.waddr, io.data, io.we)
            io.rs1 = mem[io.raddr0]
            io.rs2 = mem[io.raddr1]
            

class ROM[SIZE: int, WIDTH: int](Module):
    """
    A Parameterized ROM.
    """
    clk:    INPUT[Clock]
    addr:   INPUT[Logic[clog2(SIZE)]]
    dout:   OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        # Instantiate memory primitive
        mem = Mem[SIZE, Logic[WIDTH]](name="ROM")

        with io.clk.posedge:
            # Memory read
            io.dout = mem[io.addr]


class MemTestComplex[SIZE: int, DTYPE](Module):
    """Memory test with parameterized type from main.py."""
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    we:     INPUT[Logic[1]]
    data:   INPUT[DTYPE]
    waddr:  INPUT[Logic[clog2(SIZE)]]
    raddr:  INPUT[Logic[clog2(SIZE)]]

    out : OUTPUT[DTYPE]

    def build(self, io):
        mem = Mem[SIZE, DTYPE]()

        with io.clk.posedge, io.rst.negedge:
            mem.write(io.waddr, io.data, io.we)
            io.out = mem[io.raddr]


def test_mem_simple():
    """Test simple Logic memory."""
    print("=" * 60)
    print("Testing Mem[16, Logic[32]]")
    print("=" * 60)
    
    m = MemTestSimple[16, 32]()
    print("\nMLIR:")
    print(m.mlir())
    print("\nVerilog:")
    print(m.verilog())
    
    # Simulate
    with m.simulate() as sim:
        io = sim.io
        io.rst = 1  # Active high reset negated
        
        # Write values
        print("\nWriting values...")
        for i in range(16):
            io.we = 1
            io.addr = i
            io.data = i * 100
            sim.tick()
        
        # Read values
        print("\nReading values...")
        io.we = 0
        io.re = 1
        for i in range(16):
            io.addr = i
            sim.tick()
            expected = i * 100
            print(f"  Address {i}: got {io.out}, expected {expected}")
            assert io.out == expected, f"Memory test failed at address {i}"
    
    print("\n✓ Simple memory test passed!")


def test_mem_struct():
    """Test memory with Struct type."""
    print("\n" + "=" * 60)
    print("Testing Mem[16, Point]")
    print("=" * 60)
    
    m = MemTestStruct()
    print("\nMLIR:")
    print(m.mlir())
    print("\nVerilog:")
    print(m.verilog())
    
    print("\n✓ Struct memory compilation passed!")


def test_mem_array():
    """Test memory with Array type."""
    print("\n" + "=" * 60)
    print("Testing Mem[8, Array[4, Logic[8]]]")
    print("=" * 60)
    
    m = MemTestArray()
    print("\nMLIR:")
    print(m.mlir())
    print("\nVerilog:")
    print(m.verilog())
    
    print("\n✓ Array memory compilation passed!")


def test_memory_byte_enable():
    mem = MemoryByteEnable[512]()
    
    with mem.simulate() as sim:
        io = sim.io

        for i in range(8):
            io.we = 0b0001 << i % 4
            io.waddr = i
            io.data = 0xaabb_ccdd
            sim.tick()

        io.we = 0
        for i in range(8):
            io.raddr = i
            sim.tick()
            assert io.out == 0xaabb_ccdd & (0xff << ((i % 4) * 8))
        

def test_simple_dual_port_mem():
    test = SimpleDualPortMem[16, 32]()

    with test.simulate() as sim:
        io = sim.io
        io.rst = 1
        for i in range(16):
            io.we = 1
            io.waddr = i
            io.data = i * 10
            sim.tick()
        
        for i in range(16):
            io.we = 0
            io.raddr0 = i
            io.raddr1 = i
            sim.tick()
            assert io.rs1 == io.rs2 == i * 10


def test_rom():
    # ROM Test
    rom = ROM[16, 32]()
        
    with rom.simulate() as sim:
        # Write to ROM
        mem = sim.memories['ROM']
        mem[:16] = [i for i in range(16)]
        
        for i in range(16):
            sim.io.addr = i
            sim.tick()
            print(f"Read Addr {i}: {hex(sim.io.dout)}")
            assert sim.io.dout == i


def test_mem_complex():
    """Test memory with Array of Structs (complex type from main.py)."""
    class Point[W: int](Struct):
        x: Logic[W]
        y: Logic[W]

    dtype = Array[4, Point[7]]
    m = MemTestComplex[16, dtype]()
        
    with m.simulate() as sim:
        io = sim.io
        # Write some values
        for i in range(4):
            io.we = 1
            io.waddr = i
            io.data = [{"x": j, "y": j} for j in range(4)]
            sim.tick()
        
        # Read back and verify
        io.we = 0
        for i in range(4):
            io.raddr = i
            sim.tick()
            expected = [{"x": j, "y": j} for j in range(4)]
            assert io.out == expected, f"Failed at index {i}"
    
    print("\n✓ Complex memory (Array of Structs) test passed!")




if __name__ == "__main__":
    test_mem_simple()
    test_mem_struct()
    test_mem_array()
    test_memory_byte_enable()
    test_simple_dual_port_mem()
    test_rom()
    test_mem_complex()
    print("\n" + "=" * 60)
    print("All Mem tests passed!")
    print("=" * 60)
