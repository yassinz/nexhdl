from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Mux, Param, Map


class UartTx[CLK_FREQ: int, BAUD_RATE: int](Module):
    """
    UART Transmitter using nested Muxes for the State Machine.
    Parameters:
        CLK_FREQ: Frequency of clk in Hz (e.g., 50_000_000)
        BAUD_RATE: Target baud rate (e.g., 115_200)
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    data:   INPUT[Logic[8]]
    valid:  INPUT[Logic[1]]
    ready:  OUTPUT[Logic[1]]
    tx_pin: OUTPUT[Logic[1]]

    def build(self, io):
        CYCLES_PER_BIT = CLK_FREQ // BAUD_RATE
        BIT_WIDTH = CLK_FREQ.bit_length()
        
        IDLE, START, DATA, STOP = Logic[2](0), Logic[2](1), Logic[2](2), Logic[2](3)
        
        state      = Reg[Logic[2]](reset_value=IDLE)
        shift_reg  = Reg[Logic[8]]()
        bit_idx    = Reg[Logic[3]]()
        counter    = Reg[Logic[BIT_WIDTH]]()
        
        tick = (counter == (CYCLES_PER_BIT - 1))
        
        # Next State Logic using Map
        next_state = Map[2, Logic[2]](
            (IDLE,  Mux[Logic[2]](io.valid, START, IDLE)),
            (START, Mux[Logic[2]](tick, DATA, START)),
            (DATA,  Mux[Logic[2]](tick & (bit_idx == 7), STOP, DATA)),
            (STOP,  Mux[Logic[2]](tick, IDLE, STOP)),
            default=IDLE
        )[state]

        # Register Updates
        with io.clk.posedge, io.rst.negedge:
            state.next = next_state
            
            # Counter logic: reset if IDLE or bit-tick, otherwise increment
            counter.next = Mux[Logic[BIT_WIDTH]](tick | (state == IDLE), 
                                                Logic[BIT_WIDTH](0), 
                                                counter + 1)
            
            # Shift register: Load in IDLE, Shift in DATA
            shift_reg.next = Map[2, Logic[8]](
                (IDLE, Mux[Logic[8]](io.valid, io.data, shift_reg)),
                (DATA, Mux[Logic[8]](tick, shift_reg >> 1, shift_reg)),
                default=shift_reg
            )[state]
            
            # Bit index: Reset in START, Increment in DATA
            bit_idx.next = Map[2, Logic[3]](
                (START, Mux[Logic[3]](tick, Logic[3](0), bit_idx)),
                (DATA,  Mux[Logic[3]](tick, bit_idx + 1, bit_idx)),
                default=bit_idx
            )[state]

        # Output logic
        io.ready = (state == IDLE)
        io.tx_pin = Map[2, Logic[1]](
            (START, Logic[1](0)),
            (DATA,  shift_reg[0]),
            default=Logic[1](1) # Idle and Stop are 1
        )[state]


class UartRx[CLK_FREQ: int, BAUD_RATE: int](Module):
    """
    UART Receiver.
    Samples at the middle of each bit period.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    rx_pin: INPUT[Logic[1]]
    
    data:   OUTPUT[Logic[8]]
    valid:  OUTPUT[Logic[1]]

    def build(self, io):
        CYCLES_PER_BIT = CLK_FREQ // BAUD_RATE
        BIT_WIDTH = CLK_FREQ.bit_length()
        
        IDLE, START, DATA, STOP = Logic[2](0), Logic[2](1), Logic[2](2), Logic[2](3)
        
        state     = Reg[Logic[2]](reset_value=IDLE)
        shift_reg = Reg[Logic[8]]()
        bit_idx   = Reg[Logic[3]]()
        counter   = Reg[Logic[BIT_WIDTH]]()
        valid_reg = Reg[Logic[1]](reset_value=0)
        
        # Sampling point is in the middle of the bit period
        half_tick = (counter == (CYCLES_PER_BIT // 2 - 1))
        full_tick = (counter == (CYCLES_PER_BIT - 1))
        
        # Next State Logic
        next_state = Map[2, Logic[2]](
            (IDLE,  Mux[Logic[2]](io.rx_pin == 0, START, IDLE)), # Detect start bit (falling edge)
            (START, Mux[Logic[2]](full_tick, DATA, START)),
            (DATA,  Mux[Logic[2]](full_tick & (bit_idx == 7), STOP, DATA)),
            (STOP,  Mux[Logic[2]](full_tick, IDLE, STOP)),
            default=IDLE
        )[state]

        with io.clk.posedge, io.rst.negedge:
            state.next = next_state
            
            # Counter logic
            counter.next = Mux[Logic[BIT_WIDTH]](full_tick | (state == IDLE), 
                                                Logic[BIT_WIDTH](0), 
                                                counter + 1)
            
            # Shift register: Sample at half_tick in DATA state
            shift_reg.next = Map[2, Logic[8]](
                (DATA, Mux[Logic[8]](half_tick, io.rx_pin @ shift_reg[1:8], shift_reg)),
                default=shift_reg
            )[state]
            
            # Bit index: Increment at full_tick in DATA state
            bit_idx.next = Map[2, Logic[3]](
                (START, Mux[Logic[3]](full_tick, Logic[3](0), bit_idx)),
                (DATA,  Mux[Logic[3]](full_tick, bit_idx + 1, bit_idx)),
                default=bit_idx
            )[state]
            
            # Valid signal: High for one cycle after STOP state full_tick
            valid_reg.next = (state == STOP) & full_tick

        io.data = shift_reg
        io.valid = valid_reg



if __name__ == "__main__":
    print("--- Simulating UART Loopback ---")
    CLK_FREQ, BAUD_RATE = 1000, 100
    
    class Loopback(Module):
        clk:  INPUT[Clock]
        rst:  INPUT[Reset]
        data: INPUT[Logic[8]]
        send: INPUT[Logic[1]]
        
        out_data:  OUTPUT[Logic[8]]
        out_valid: OUTPUT[Logic[1]]
        
        def build(self, io):
            tx = UartTx[CLK_FREQ, BAUD_RATE](
                clk=io.clk, rst=io.rst, data=io.data, valid=io.send
            )
            rx = UartRx[CLK_FREQ, BAUD_RATE](
                clk=io.clk, rst=io.rst, rx_pin=tx.tx_pin
            )
            io.out_data = rx.data
            io.out_valid = rx.valid

    dut = Loopback()
    
    with dut.simulate() as sim:
        sim.vcd("uart_loopback.vcd")
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        
        # Send 0x12
        sim.io.data = 0x12
        sim.io.send = 1
        sim.tick()
        sim.io.send = 0
        
        # Wait for valid signal (approx 10 bits * 10 cycles = 100 cycles)
        max_cycles = 150
        found = False
        for i in range(max_cycles):
            sim.tick()
            if sim.io.out_valid:
                print(f"Received: {hex(sim.io.out_data)} at cycle {i}")
                assert sim.io.out_data == 0x12
                found = True
                break
        
        assert found, "Timeout: Out valid never went high"
        
        # Send 0x8F
        sim.io.data = 0x8F
        sim.io.send = 1
        sim.tick()
        sim.io.send = 0
        
        found = False
        for i in range(max_cycles):
            sim.tick()
            if sim.io.out_valid:
                print(f"Received: {hex(sim.io.out_data)} at cycle {i}")
                assert sim.io.out_data == 0x8F
                found = True
                break
        
        assert found, "Timeout: Out valid never went high"

    print("\n✓ UART Loopback Successful!")
