from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Param, Mux

class CRC32(Module):
    """
    CRC-32 Generator (Ethernet Polynomial: 0x04C11DB7)
    
    This module implements a bit-serial CRC-32 calculation.
    It demonstrates:
    1. Bit-wise operations for feedback logic.
    2. Looping in Python to generate dense hardware logic.
    3. State management via registers.
    """
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    data_in:  INPUT[Logic[8]]
    valid:    INPUT[Logic[1]]
    
    crc_out:  OUTPUT[Logic[32]]

    def build(self, io):
        # CRC polynomial: 0x04C11DB7
        POLYNOMIAL = 0x04C11DB7
        
        # Current CRC state
        crc_reg = Reg[Logic[32]](init=0xFFFFFFFF)
        
        # Combinatorial logic to calculate the next CRC value for 8 bits of data
        # We calculate this bit-by-bit using a Python loop to generate the unrolled logic
        current_crc = crc_reg
        for bit in range(8):
            # Bit-serial CRC logic:
            # If the MSB of CRC XOR data_bit is 1, XOR with polynomial
            msb = current_crc[31] ^ io.data_in[7-bit]
            feedback = Logic[32](POLYNOMIAL)
            
            # Use a Mux-like behavior via bitwise logic
            # (current_crc << 1) ^ (msb ? polynomial : 0)
            # In NexHDL, we can use the .replicate method to create a mask
            mask = msb.replicate(32)
            current_crc = (current_crc << 1) ^ (feedback & mask)
            
        with io.clk.posedge, io.rst.negedge:
            # Update CRC if input is valid
            crc_reg.next = Mux[Logic[32]](io.valid, current_crc, crc_reg)
            
        # Final result is usually inverted
        io.crc_out = ~crc_reg

if __name__ == "__main__":
    print("--- NexHDL CRC-32 Example ---")
    crc = CRC32()
    print(crc.verilog())
    
    with crc.simulate() as sim:
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1
        
        # Test case: CRC32 of "123456789" is 0xFC891918
        # Data bits: 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39
        test_data = [ord(c) for c in "123456789"]
        
        print(f"Calculating CRC for: {[hex(d) for d in test_data]}")
        sim.io.valid = 1
        for d in test_data:
            sim.io.data_in = d
            sim.tick()
            
        sim.io.valid = 0
        print(f"Final CRC: {hex(sim.io.crc_out)}")
        assert sim.io.crc_out == 0xFC891918