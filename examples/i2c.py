from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Mux, Param, Map


class I2cMaster[CLK_DIV: int](Module):
    """
    Simplified I2C Master (Write only).
    Parameters:
        CLK_DIV: Cycles per SCLK period. Must be multiple of 4.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    
    # User Interface
    addr:     INPUT[Logic[7]]
    data:     INPUT[Logic[8]]
    start:    INPUT[Logic[1]]
    ready:    OUTPUT[Logic[1]]
    busy:     OUTPUT[Logic[1]]
    ack_err:  OUTPUT[Logic[1]]
    
    # I2C Bus (Open-Drain Model)
    scl_o:    OUTPUT[Logic[1]]
    sda_o:    OUTPUT[Logic[1]]
    sda_i:    INPUT[Logic[1]]

    def build(self, io):
        Q_PERIOD = CLK_DIV // 4 
        BIT_W = CLK_DIV.bit_length()
        
        IDLE, START, ADDR, ACK1, DATA, ACK2, STOP = range(7)
        states = [Logic[3](i) for i in range(7)]
        (S_IDLE, S_START, S_ADDR, S_ACK1, S_DATA, S_ACK2, S_STOP) = states
        
        state      = Reg[Logic[3]](reset_value=S_IDLE)
        shift_reg  = Reg[Logic[8]]()
        bit_idx    = Reg[Logic[3]]()
        counter    = Reg[Logic[BIT_W]]()
        phase      = Reg[Logic[2]](reset_value=0) # 0, 1, 2, 3
        
        scl_o_reg  = Reg[Logic[1]](reset_value=1)
        sda_o_reg  = Reg[Logic[1]](reset_value=1)
        ack_error  = Reg[Logic[1]](reset_value=0)
        
        q_tick = (counter == (Q_PERIOD - 1))
        p_done = q_tick & (phase == 3)
        
        # Next State Logic
        next_state = Map[3, Logic[3]](
            (S_IDLE,  Mux[Logic[3]](io.start, S_START, S_IDLE)),
            (S_START, Mux[Logic[3]](p_done, S_ADDR, S_START)),
            (S_ADDR,  Mux[Logic[3]](p_done & (bit_idx == 7), S_ACK1, S_ADDR)),
            (S_ACK1,  Mux[Logic[3]](p_done, S_DATA, S_ACK1)),
            (S_DATA,  Mux[Logic[3]](p_done & (bit_idx == 7), S_ACK2, S_DATA)),
            (S_ACK2,  Mux[Logic[3]](p_done, S_STOP, S_ACK2)),
            (S_STOP,  Mux[Logic[3]](p_done, S_IDLE, S_STOP)),
            default=S_IDLE
        )[state]

        with io.clk.posedge, io.rst.negedge:
            state.next = next_state
            counter.next = Mux[Logic[BIT_W]](q_tick | (state == S_IDLE), Logic[BIT_W](0), counter + 1)
            
            # Phase update
            phase.next = Mux[Logic[2]](state == S_IDLE, Logic[2](0),
                         Mux[Logic[2]](q_tick, phase + 1, phase))
            
            # Shift Register & Bit Index logic
            is_start_init = (state == S_IDLE) & io.start
            is_bit_shift  = ((state == S_ADDR) | (state == S_DATA)) & q_tick & (phase == 2)
            
            shift_reg.next = Mux[Logic[8]](is_start_init, io.addr @ Logic[1](0),
                             Mux[Logic[8]](is_bit_shift, shift_reg << 1,
                             Mux[Logic[8]]((state == S_ACK1) & p_done, io.data, shift_reg)))
            
            bit_idx.next = Mux[Logic[3]](is_start_init | ((state == S_ACK1) & p_done), Logic[3](0),
                           Mux[Logic[3]](is_bit_shift, bit_idx + 1, bit_idx))

            # Bus Line Updates
            # Phase 0: SDA Change, Phase 1: SCL High, Phase 2: SDA Sample, Phase 3: SCL Low
            
            # SDA Output Logic
            next_sda = Map[3, Logic[1]](
                (S_START, Mux[Logic[1]](phase == 0, Logic[1](0), sda_o_reg)),
                (S_ADDR,  Mux[Logic[1]](phase == 3, shift_reg[7], sda_o_reg)),
                (S_ACK1,  Mux[Logic[1]](phase == 3, Logic[1](1), sda_o_reg)), # Release for ACK
                (S_DATA,  Mux[Logic[1]](phase == 3, shift_reg[7], sda_o_reg)),
                (S_ACK2,  Mux[Logic[1]](phase == 3, Logic[1](1), sda_o_reg)), # Release for ACK
                (S_STOP,  Mux[Logic[1]](phase == 0, Logic[1](0), 
                          Mux[Logic[1]](phase == 1, Logic[1](1), sda_o_reg))),
                default=Logic[1](1)
            )[state]
            sda_o_reg.next = Mux[Logic[1]](q_tick, next_sda, sda_o_reg)

            # SCL Output Logic
            next_scl = Map[3, Logic[1]](
                (S_START, Logic[1](1)),
                (S_ADDR,  Mux[Logic[1]](phase == 0, Logic[1](1), Mux[Logic[1]](phase == 2, Logic[1](0), scl_o_reg))),
                (S_ACK1,  Mux[Logic[1]](phase == 0, Logic[1](1), Mux[Logic[1]](phase == 2, Logic[1](0), scl_o_reg))),
                (S_DATA,  Mux[Logic[1]](phase == 0, Logic[1](1), Mux[Logic[1]](phase == 2, Logic[1](0), scl_o_reg))),
                (S_ACK2,  Mux[Logic[1]](phase == 0, Logic[1](1), Mux[Logic[1]](phase == 2, Logic[1](0), scl_o_reg))),
                (S_STOP,  Logic[1](1)),
                default=Logic[1](1)
            )[state]
            # SCL is special: only changes if state is not IDLE
            scl_o_reg.next = Mux[Logic[1]](state == S_IDLE, Logic[1](1), 
                             Mux[Logic[1]](q_tick, next_scl, scl_o_reg))

            # ACK Capture
            is_ack_sample = ((state == S_ACK1) | (state == S_ACK2)) & q_tick & (phase == 1)
            ack_error.next = Mux[Logic[1]](is_start_init, Logic[1](0),
                             Mux[Logic[1]](is_ack_sample, ack_error | io.sda_i, ack_error))

        io.ready   = (state == S_IDLE)
        io.busy    = (state != S_IDLE)
        io.ack_err = ack_error
        io.scl_o   = scl_o_reg
        io.sda_o   = sda_o_reg


if __name__ == "__main__":
    print("--- Simulating I2C Master ---")
    # Low frequency for fast simulation
    CLK_DIV = 16
    i2c = I2cMaster[CLK_DIV]()
    print(i2c.verilog())
    
    with i2c.simulate() as sim:
        sim.vcd("i2c_master.vcd")
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        sim.io.sda_i = 0 # Force ACK
        
        # Start transfer to addr 0x55 with data 0xAA
        sim.io.addr  = 0x55
        sim.io.data  = 0xAA
        sim.io.start = 1
        sim.tick()
        sim.io.start = 0
        
        # Monitor progress
        for _ in range(500):
            sim.tick()
            if sim.io.ready:
                break
        
        print(f"I2C Transfer Finished. Ack Error: {sim.io.ack_err}")
        assert sim.io.ack_err == 0
    
    print("\n✓ I2C Example Successful!")
