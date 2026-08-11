from nexhdl import Module, INPUT, OUTPUT, Logic

class LogicGates[WIDTH: int](Module):
    """
    Demonstrates basic bitwise and reduction operations.
    """
    a:      INPUT[Logic[WIDTH]]
    b:      INPUT[Logic[WIDTH]]
    
    # Bitwise results
    and_o:  OUTPUT[Logic[WIDTH]]
    or_o:   OUTPUT[Logic[WIDTH]]
    xor_o:  OUTPUT[Logic[WIDTH]]
    not_a:  OUTPUT[Logic[WIDTH]]
    
    # Reduction results (collapsing bits to 1-bit)
    all_ones:  OUTPUT[Logic[1]] # AND reduction
    any_one:   OUTPUT[Logic[1]] # OR reduction
    parity:    OUTPUT[Logic[1]] # XOR reduction

    def build(self, io):
        # Bitwise Ops
        io.and_o = io.a & io.b
        io.or_o  = io.a | io.b
        io.xor_o = io.a ^ io.b
        io.not_a = ~io.a
        
        # Reduction Ops
        # In NexHDL, we can use built-in methods or logic comparisons
        io.all_ones = (io.a == ((1 << WIDTH) - 1))
        io.any_one  = (io.a != 0)
        io.parity   = io.a.parity() # Sum of bits mod 2

if __name__ == "__main__":
    gates = LogicGates[8]()
    print(f"--- LogicGates for WIDTH={gates.WIDTH} ---")
    print(gates.verilog())
    
    with gates.simulate() as sim:
        sim.io.a = 0b10101010
        sim.io.b = 0b11110000
        sim.step()
        
        print(f"A: {bin(sim.io.a)}, B: {bin(sim.io.b)}")
        print(f"AND: {bin(sim.io.and_o)}")
        print(f"OR:  {bin(sim.io.or_o)}")
        print(f"XOR: {bin(sim.io.xor_o)}")

        print(f"All ones: {sim.io.all_ones}")
        print(f"Any one: {sim.io.any_one}")
        print(f"Parity of A: {sim.io.parity}")
