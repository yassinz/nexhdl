from nexhdl import *

class ShiftRegister[WIDTH: int](Module):
    """
    A simple 4-stage shift register.
    Demonstrates connecting registers in a chain.
    """
    clk:     INPUT[Clock]
    rst:     INPUT[Reset]
    data_in: INPUT[Logic[WIDTH]]
    
    # Outputs from each stage
    stage0:  OUTPUT[Logic[WIDTH]]
    stage1:  OUTPUT[Logic[WIDTH]]
    stage2:  OUTPUT[Logic[WIDTH]]
    stage3:  OUTPUT[Logic[WIDTH]]

    def build(self, io):
        # Create 4 independent registers
        r0 = Reg[Logic[WIDTH]]()
        r1 = Reg[Logic[WIDTH]]()
        r2 = Reg[Logic[WIDTH]]()
        r3 = Reg[Logic[WIDTH]]()

        with io.clk.posedge, io.rst.negedge:
            # Shift chain: in -> r0 -> r1 -> r2 -> r3
            r0.next = io.data_in
            r1.next = r0
            r2.next = r1
            r3.next = r2
        
        # Connect outputs
        io.stage0 = r0
        io.stage1 = r1
        io.stage2 = r2
        io.stage3 = r3

if __name__ == "__main__":
    sr = ShiftRegister[8]()
    print(f"--- ShiftRegister[{sr.WIDTH}] Verilog ---")
    print(sr.verilog())
    
    with sr.simulate() as sim:
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1
        
        for i in range(1, 6):
            sim.io.data_in = i * 10
            sim.tick()
            print(
                f"Tick {i}: In={sim.io.data_in:2},"
                f"Out=[{sim.io.stage0:2},"
                f"{sim.io.stage1:2},"
                f"{sim.io.stage2:2},"
                f"{sim.io.stage3:2}]"
            )
