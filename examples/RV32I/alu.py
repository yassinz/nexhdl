from nexhdl import *
from random import randrange





class ALU[WIDTH: int](Module):
    rs1:      INPUT[Logic[WIDTH]]
    rs2:      INPUT[Logic[WIDTH]]
    inst:     INPUT[Logic[32]]

    out:      OUTPUT[Logic[WIDTH]]
    taken:    OUTPUT[Logic[1]]

    def build(self, io):
        sel = io.inst[30]
        func  = io.inst[12:15]
        imm_i = io.inst[20:32]

        rs1 = io.rs1
        rs2_imm = Mux[WIDTH](io.inst[5], io.rs2, imm_i.sext(WIDTH))
        shamt = rs2_imm[0:6].zext(WIDTH)
        
        ADD_SUB = Mux[WIDTH](sel & io.inst[5], rs1 - rs2_imm, rs1 + rs2_imm)
        SLL = rs1 << shamt
        SLT = (rs1.si < rs2_imm.si).zext(WIDTH)
        SLTIU = (rs1 < rs2_imm).zext(WIDTH)
        XOR = rs1 ^ rs2_imm
        SRA_SRL = Mux[WIDTH](sel, rs1.si >> shamt, rs1 >> shamt)
        OR = rs1 | rs2_imm
        AND = rs1 & rs2_imm

        alu = Array[8, WIDTH]([ADD_SUB, SLL, SLT, SLTIU, XOR, SRA_SRL, OR, AND])
        io.out = alu[func]

        
        BEQ = (rs1 == rs2_imm)
        BNE = ~BEQ
        BLT = SLT[0]
        BGE = ~BLT
        BLTU = SLTIU[0]
        BGEU = ~BLTU

        taken = Array[8, 1]([BEQ, BNE, 0, 0, BLT, BGE, BLTU, BGEU])
        io.taken = taken[func]




# riscv assembly
"""
    li x2, -51
    li x3, 13

    addi x1, x2, 1
    slti x1, x2, -1
    sltiu x1, x2, 1
    xori x1, x2, 1
    ori  x1, x2, 1
    andi x1, x2, 1
    slli x1, x2, 1
    srli x1, x2, 1
    srai x1, x2, 1

    add x1, x2, x3
    sub x1, x2, x3
    sll x1, x2, x3
    slt x1, x2, x3
    sltu x1, x2, x3
    xor x1, x2, x3
    srl x1, x2, x3
    sra x1, x2, x3
    or  x1, x2, x3
    and x1, x2, x3
"""


from ctypes import c_uint64, c_int32


u64 = lambda x: c_uint64(x).value
i32 = lambda x: c_int32(x).value

def hex32(x): return hex(x)[2:].zfill(8)
def hex64(x): return hex(x)[2:].zfill(16)


def test_ALU(W):
    alu = ALU[W]()
    #print(alu.mlir())
    #print(alu.verilog())

    insts_32b  = [0x00110093, 0xfff12093, 0x00113093, 0x00114093,
                  0x00116093, 0x00117093, 0x00111093, 0x00115093,
                  0x40115093, 0x003100b3, 0x403100b3, 0x003110b3,
                  0x003120b3, 0x003130b3, 0x003140b3, 0x003150b3,
                  0x403150b3, 0x003160b3, 0x003170b3]

    eval_data = [0xffffffce ,0x1 ,0x0 ,0xffffffcc ,0xffffffcd ,0x1,
                 0xffffff9a ,0x7fffffe6 ,0xffffffe6 ,0xffffffda,
                 0xffffffc0 ,0xfff9a000 ,0x1 ,0x0 ,0xffffffc0 ,0x7ffff,
                 0xffffffff ,0xffffffcd ,0xd]
    
    if W == 64:
        eval_data[7]  = 0x7fffffffffffffe6
        eval_data[15] = 0x0007ffffffffffff

    with Simulator(alu.module, alu.name) as sim:
        io = sim.io

        io.rs1 = -51 if W==32 else u64(i32(-51))
        io.rs2 = 13 if W==32 else u64(i32(13))

        hexx = hex32 if W==32 else hex64
        cast = lambda x: x if W==32 else u64(i32(x))

        for inst, eval_d in zip(insts_32b, eval_data):
            io.inst = inst
            sim.step()
            eval_d = cast(eval_d)

            # fix SRA SRL for 64bit
            if W == 64:
                if inst == 0x00115093: eval_d = 0x7fffffffffffffe6
                if inst == 0x003150b3: eval_d = 0x0007ffffffffffff

            print(hexx(io.out), hexx(eval_d), io.out == eval_d)
            assert io.out == eval_d



if __name__ == '__main__':
    test_ALU(32)
    test_ALU(64)