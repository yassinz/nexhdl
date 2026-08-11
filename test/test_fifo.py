#!/usr/bin/env python3
"""Test file for Fifo primitive."""

from nexhdl import *


class FifoTest(Module):
    """Simple FIFO test module."""
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    we:       INPUT[Logic[1]]
    re:       INPUT[Logic[1]]
    data_in:  INPUT[Logic[32]]
    
    data_out: OUTPUT[Logic[32]]
    full:     OUTPUT[Logic[1]]
    empty:    OUTPUT[Logic[1]]
    
    def build(self, io):
        fifo = Fifo[8, Logic[32]]()
        
        with io.clk.posedge, io.rst.negedge:
            # Clean push/pop API
            fifo.push(io.data_in, io.we)
            io.data_out = fifo.pop(io.re)

        io.full = fifo.full
        io.empty = fifo.empty


def test_fifo():
    print("=" * 60)
    print("Testing Fifo[8, Logic[32]]")
    print("=" * 60)
    
    m = FifoTest()
    print("\nMLIR:")
    print(m.mlir())
    print("\nVerilog:")
    print(m.verilog())
    
    # Simulate
    with m.simulate() as sim:
        io = sim.io
        io.rst = 1
        
        # Write 8 values
        print("\nWriting values...")
        for i in range(8):
            io.we = 1
            io.re = 0
            io.data_in = i * 10
            sim.tick()
            print(f"  Push {i*10}: full={io.full}, empty={io.empty}")
        
        # Read 8 values
        print("\nReading values...")
        io.we = 0
        for i in range(8):
            io.re = 1
            sim.tick()
            expected = i * 10
            print(f"  Pop: got {io.data_out}, expected {expected}")
            assert io.data_out == expected, f"FIFO failed"
    
    print("\n✓ FIFO test passed!")


if __name__ == "__main__":
    test_fifo()
