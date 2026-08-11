from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Mux, Param, Map, Wire


class SpiMaster[CLK_DIV: int](Module):
    """
    SPI Master (CPOL=0, CPHA=0).
    Parameters:
        CLK_DIV: Clock division factor (SCLK freq = CLK / CLK_DIV). 
                 Must be an even number >= 2.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    
    # User Interface
    data_in:  INPUT[Logic[8]]
    start:    INPUT[Logic[1]]
    ready:    OUTPUT[Logic[1]]
    data_out: OUTPUT[Logic[8]]
    valid:    OUTPUT[Logic[1]]
    
    # SPI Bus
    sclk:   OUTPUT[Logic[1]]
    mosi:   OUTPUT[Logic[1]]
    miso:   INPUT[Logic[1]]
    cs_n:   OUTPUT[Logic[1]]

    def build(self, io):
        HALF_PERIOD = CLK_DIV // 2
        COUNT_WIDTH = CLK_DIV.bit_length()
        
        IDLE, TRANSFER, DONE = Logic[2](0), Logic[2](1), Logic[2](2)
        
        state      = Reg[Logic[2]](reset_value=IDLE)
        shift_reg  = Reg[Logic[8]]()
        rx_reg     = Reg[Logic[8]]()
        bit_idx    = Reg[Logic[3]]()
        counter    = Reg[Logic[COUNT_WIDTH]]()
        sclk_reg   = Reg[Logic[1]](reset_value=0)
        
        # Timing ticks
        tick = (counter == (HALF_PERIOD - 1))
        
        # Next State Logic
        next_state = Map[2, Logic[2]](
            (IDLE,     Mux[Logic[2]](io.start, TRANSFER, IDLE)),
            (TRANSFER, Mux[Logic[2]](tick & sclk_reg & (bit_idx == 7), DONE, TRANSFER)),
            (DONE,     IDLE),
            default=IDLE
        )[state]

        with io.clk.posedge, io.rst.negedge:
            state.next = next_state
            
            # Counter logic
            counter.next = Mux[Logic[COUNT_WIDTH]](tick | (state == IDLE), 
                                                 Logic[COUNT_WIDTH](0), 
                                                 counter + 1)
            
            # SCLK Generation (Toggles on every tick in TRANSFER state)
            sclk_reg.next = Mux[Logic[1]](state == TRANSFER,
                            Mux[Logic[1]](tick, ~sclk_reg, sclk_reg),
                            Logic[1](0))
            
            # Transfer logic
            is_starting = (state == IDLE) & io.start
            is_sampling = (state == TRANSFER) & tick & (~sclk_reg) # Rising edge of SCLK
            is_shifting = (state == TRANSFER) & tick & sclk_reg    # Falling edge of SCLK
            
            # MOSI Shift Register (MSB first)
            shift_reg.next = Mux[Logic[8]](is_starting, io.data_in,
                             Mux[Logic[8]](is_shifting, shift_reg << 1, shift_reg))
            
            # MISO Capture
            rx_reg.next = Mux[Logic[8]](is_sampling, rx_reg[0:7] @ io.miso, rx_reg)
            
            # Bit Index
            bit_idx.next = Mux[Logic[3]](is_starting, Logic[3](0),
                           Mux[Logic[3]](is_shifting, bit_idx + 1, bit_idx))

        # Output logic
        io.ready    = (state == IDLE)
        io.valid    = (state == DONE)
        io.data_out = rx_reg
        io.sclk     = sclk_reg
        io.mosi     = shift_reg[7]
        io.cs_n     = (state == IDLE)


if __name__ == "__main__":
    print("--- Simulating SPI Master Loopback ---")
    
    class SpiLoopback(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        din: INPUT[Logic[8]]
        run: INPUT[Logic[1]]
        dout: OUTPUT[Logic[8]]
        vld:  OUTPUT[Logic[1]]
        
        def build(self, io):
            # We use a wire for late-binding the loopback
            loopback = Wire[Logic[1]]()
            
            # CLK_DIV=4 means 4 cycles per SCLK period
            master = SpiMaster[4](
                clk=io.clk, rst=io.rst, 
                data_in=io.din, start=io.run,
                miso=loopback
            )
            
            # Connect the wire
            loopback.assign = master.mosi
            
            io.dout = master.data_out
            io.vld  = master.valid

    dut = SpiLoopback()
    
    with dut.simulate() as sim:
        sim.vcd("spi_loopback.vcd")
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        
        # Transfer 0xA5
        sim.io.din = 0xA5
        sim.io.run = 1
        sim.tick()
        sim.io.run = 0
        
        # Wait for completion (8 bits * 4 cycles = 32 cycles + margin)
        for i in range(50):
            sim.tick()
            if sim.io.vld:
                received = sim.io.dout
                print(f"Received: {hex(received)} and vld={sim.io.vld} at cycle {i}")
                assert received == 0xA5
                break
        else:
            print("Error: Timeout")
            exit(1)

    print("\n✓ SPI Example Successful!")
