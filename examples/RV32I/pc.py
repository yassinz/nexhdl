from nexhdl import *

from random import randrange
from inst import Inst



width_check = Param[int](lambda x: x in [32, 64], "PC width must be 32 or 64")

class PC[WIDTH: width_check](Module):
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    rs1:      INPUT[Logic[WIDTH]]
    inst:     INPUT[Logic[32]]
    taken:    INPUT[Logic[1]]
    
    out:      OUTPUT[Logic[WIDTH]]

    def build(self, io):
        inst = Inst(io.inst)
        pc = Reg[WIDTH]()

        BRANCH = pc + inst.imm_b().sext(WIDTH)
        JALR   = (io.rs1 + inst.imm_i().sext(WIDTH)) # & ~1   # Clear LSB
        JAL    = pc + inst.imm_j().sext(WIDTH)
        NEXT   = pc + 4

        B_NEXT = Mux[WIDTH](io.taken, BRANCH, NEXT)

        next = Map[5, WIDTH](
                (0b11000, B_NEXT),
                (0b11001, JALR),
                (0b11011, JAL),
                default=NEXT,
        )
        
        with io.clk.posedge, io.rst.negedge:
            pc.next = next[inst.opcode()]
        
        io.out = pc





def test_pc():
    pc = PC[64]()
    pc.compile()
    print(pc.mlir())
    print(pc.verilog())
    
    with Simulator(pc.module, pc.name) as sim:
        io = sim.io
        io.rst = 0
        sim.tick()
        io.rst = 1

        # test BRANCH
        io.inst = 0b0000000000000000000000000_11000_11
        io.taken = 1
        sim.tick()
        sim.tick()
        sim.tick()
        assert io.out == 0
            
        io.taken = 0
        sim.tick()
        sim.tick()
        assert io.out == 0x8

        io.rst = 0
        sim.tick()
        io.rst = 1

        # Test JAL
        io.inst = 0b0000000000000100000000000_11011_11
        sim.tick()
        assert io.out == 0x40000
        sim.tick()
        assert io.out == 0x80000

        io.rst = 0
        sim.tick()
        io.rst = 1

        # test JALR
        io.inst = 0b0000000000000000000000000_11001_11
        io.rs1 = 0xff
        sim.tick()
        assert io.out == 0xff
        io.rs1 = 0xffcc
        sim.tick()
        assert io.out == 0xffcc



if __name__ == "__main__":
    test_pc()