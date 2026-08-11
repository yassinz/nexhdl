from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Mux


class HandshakeBuffer[T](Module):
    """
    A simple stage module that implements Ready/Valid handshake logic.
    Provides a 1-deep buffer for the data.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    
    # Input Interface
    in_data:  INPUT[T]
    in_valid: INPUT[Logic[1]]
    in_ready: OUTPUT[Logic[1]]
    
    # Output Interface
    out_data:  OUTPUT[T]
    out_valid: OUTPUT[Logic[1]]
    out_ready: INPUT[Logic[1]]

    def build(self, io):
        # Register to store the data
        data_reg = Reg[T]()
        # Register to track if the buffer is full
        full_reg = Reg[Logic[1]](reset_value=0)
        
        # Internal Logic: Handshake state machine
        # We can accept data if our buffer is empty OR the downstream is ready to receive
        can_accept = (~full_reg) | io.out_ready
        
        # We present valid data if our buffer is full
        io.out_valid = full_reg
        io.out_data  = data_reg
        io.in_ready  = can_accept
        
        with io.clk.posedge, io.rst.negedge:
            # Update 'full' status
            # If we accepted data this cycle, full=1
            # If we didn't accept but downstream took data, full=0
            is_pushing = io.in_valid & can_accept
            is_popping = full_reg & io.out_ready
            
            full_reg.next = Mux[Logic[1]](is_pushing, Logic[1](1), 
                            Mux[Logic[1]](is_popping, Logic[1](0), full_reg))
            
            # Store data when pushing
            data_reg.next = Mux[T](is_pushing, io.in_data, data_reg)


if __name__ == "__main__":
    print("--- Simulating HandshakeBuffer ---")
    # Buffer for 16-bit logic values
    buffer = HandshakeBuffer[Logic[16]]()

    with buffer.simulate() as sim:
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        
        # 1. Immediate Transfer
        print("Test 1: Immediate Transfer")
        sim.io.in_data = 0x1234
        sim.io.in_valid = 1
        sim.io.out_ready = 1
        sim.tick()
        # Data should have moved to output register
        print(f"  Out: {hex(sim.io.out_data)} (valid: {sim.io.out_valid})")
        assert sim.io.out_data == 0x1234
        assert sim.io.out_valid == 1
        
        # 2. Backpressure
        print("Test 2: Backpressure (Consumer not ready)")
        sim.io.out_ready = 0
        sim.io.in_data = 0x5678
        sim.io.in_valid = 1
        sim.tick()
        # Buffer is now full, in_ready should be 0
        print(f"  Buffer full. In_Ready: {sim.io.in_ready}")
        assert sim.io.in_ready == 0
        
        # 3. Release backpressure
        print("Test 3: Release backpressure")
        sim.io.in_valid = 0
        sim.io.out_ready = 1
        sim.tick()
        # Data should be gone
        print(f"  Buffer empty. Out_Valid: {sim.io.out_valid}")
        assert sim.io.out_valid == 0
        
    print("\n✓ Handshake Example Successful!")
