from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Mux

class Counter(Module):
    """
    A 16-bit counter with enable and synchronous reset.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    en:     INPUT[Logic[1]]
    count:  OUTPUT[Logic[16]]

    def build(self, io):
        # Create a 16-bit register
        # It inherits Logic[16] methods, so we can increment it directly
        r = Reg[Logic[16]](reset_value=0)

        # Sequential logic context
        with io.clk.posedge, io.rst.negedge:
            # Update register based on enable
            r.next = Mux[Logic[16]](io.en, r + 1, r)

        # Drive output
        io.count = r

if __name__ == "__main__":
    dut = Counter()
    print(dut.verilog())

    with dut.simulate() as sim:
        sim.io.rst = 0 # Active low reset
        sim.tick()
        sim.io.rst = 1
        sim.io.en = 1
        
        print("Ticking counter...")
        for _ in range(5):
            sim.tick()
            print(f"Count: {sim.io.count}")
