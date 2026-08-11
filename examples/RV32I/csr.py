from nexhdl import *
from circt.dialects import debug




class CSR[WIDTH: int](Module):
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    rs1 :   INPUT[Logic[WIDTH]]
    inst:   INPUT[Logic[32]]

    out : OUTPUT[Logic[WIDTH]]

    def build(self, io):
        cycles = Reg[64]()

        with io.clk.posedge, io.rst.negedge:
            cycles.next = cycles + 1
        
        time = cycles >> 4

        csr_map = Map[12, WIDTH](
            (0xc00, cycles[0:32]),  # cyclel
            (0xc01, time[0:32]),    # timel
            (0xc02, cycles[0:32]),  # instretl

            (0xc80, cycles[32:64]), # cycleh
            (0xc81, time[32:64]),   # timeh
            (0xc82, cycles[32:64]), # instreth
            default = 0,
        )

        addr = io.inst[20:32]
        io.out = csr_map[addr]



bin8 = lambda x: format(x, '08b')

def test():
    csr = CSR[32]()
    csr.compile()
    print(csr.verilog())
    with csr.simulate() as sim:
        io = sim.io
        io.rst = 1

        io.inst = eval(f"0b0000{bin8(0xc00)}_00001_000_00001_00000_11")
        for i in range(10):
            sim.tick()
            print(io.out)
            assert io.out == i + 1
        


if __name__ == "__main__":
    test()


