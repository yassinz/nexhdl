from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Mem, clog2, Param


class SinglePortRAM[SIZE: int, WIDTH: int](Module):
    """
    A Parameterized Single-Port RAM.
    Supports a single address for both read and write operations.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    we:     INPUT[Logic[1]]
    addr:   INPUT[Logic[clog2(SIZE)]]
    din:    INPUT[Logic[WIDTH]]
    dout:   OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        # Instantiate memory primitive
        mem = Mem[SIZE, Logic[WIDTH]]()
        
        with io.clk.posedge, io.rst.negedge:
            # Memory read (results in next cycle)
            io.dout = mem[io.addr]
            
            # Memory write
            mem.write(io.addr, io.din, io.we)


class DualPortRAM[SIZE: int, WIDTH: int](Module):
    """
    A Parameterized Dual-Port RAM.
    Allows concurrent read from one address and write to another.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    
    # Write Port
    we:     INPUT[Logic[1]]
    waddr:  INPUT[Logic[clog2(SIZE)]]
    din:    INPUT[Logic[WIDTH]]
    
    # Read Port
    raddr:  INPUT[Logic[clog2(SIZE)]]
    dout:   OUTPUT[Logic[WIDTH]]
    
    def build(self, io):
        mem = Mem[SIZE, Logic[WIDTH]]()
        
        with io.clk.posedge, io.rst.negedge:
            # Concurrent read/write
            io.dout = mem[io.raddr]
            mem.write(io.waddr, io.din, io.we)



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
            # Memory read (results in next cycle)
            io.dout = mem[io.addr]






if __name__ == "__main__":
    # 1. Single Port RAM Test
    print("--- Simulating SinglePortRAM ---")
    spram = SinglePortRAM[16, 32]()
    
    with spram.simulate() as sim:
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        
        # Write to index 5
        sim.io.we = 1
        sim.io.addr = 5
        sim.io.din = 0xABCD1234
        sim.tick()
        
        # Read from index 5
        sim.io.we = 0
        sim.io.addr = 5
        sim.tick()
        
        print(f"Read Addr 5: {hex(sim.io.dout)}")
        assert sim.io.dout == 0xABCD1234

    # 2. Dual Port RAM Test
    print("\n--- Simulating DualPortRAM ---")
    dpram = DualPortRAM[64, 16]()
    
    with dpram.simulate() as sim:
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        
        # Simultaneously write to addr 10 and read from unspecified addr
        sim.io.we = 1
        sim.io.waddr = 10
        sim.io.din = 0xBEEF
        sim.io.raddr = 0
        sim.tick()
        
        # Read back from addr 10 while writing to addr 11
        sim.io.we = 1
        sim.io.waddr = 11
        sim.io.din = 0xCAFE
        sim.io.raddr = 10
        sim.tick()
        
        print(f"Read Addr 10: {hex(sim.io.dout)}")
        assert sim.io.dout == 0xBEEF
        
        # Read from addr 11
        sim.io.we = 0
        sim.io.raddr = 11
        sim.tick()
        print(f"Read Addr 11: {hex(sim.io.dout)}")
        assert sim.io.dout == 0xCAFE

    # 3. ROM Test
    print("\n--- Simulating ROM ---")
    rom = ROM[16, 32]()
    print(rom.verilog())
    
    with rom.simulate() as sim:
        # Write to ROM
        mem = sim.memories['ROM']
        mem[:16] = [i for i in range(16)]
        print(mem[:])
        
        for i in range(16):
            sim.io.addr = i
            sim.tick()
            print(f"Read Addr {i}: {hex(sim.io.dout)}")
            assert sim.io.dout == i

    print("\n✓ Memory Examples Successful!")
