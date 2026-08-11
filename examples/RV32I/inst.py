from nexhdl import *
from random import randrange






class Inst(Struct):
    inst: Logic[32]
    
    def opcode(self): return self.inst[2:7]
    def rd(self):     return self.inst[7:12]
    def rs1(self):    return self.inst[15:20]
    def rs2(self):    return self.inst[20:25]
    def funct3(self): return self.inst[12:15]
    def funct7(self): return self.inst[25:32]
    def sel(self):    return self.inst[30]

    def imm_i(self):
        return self.inst[20:32].sext(32)
    def imm_s(self):
        imm = self.inst[25:32] @ self.inst[7:12]
        return imm.sext(32)
    def imm_u(self):
        return self.inst[12:32] @ Logic[12](0)
    def imm_b(self):
        imm = (self.inst[31] @ self.inst[7] @ self.inst[25:31] @ self.inst[8:12] @ Logic[1](0))
        return imm.sext(32)
    def imm_j(self):
        imm = (self.inst[31] @ self.inst[12:20] @ self.inst[20] @ self.inst[21:31] @ Logic[1](0))
        return imm.sext(32)
    
    

class InstTest(Module):
    inst:     INPUT[Logic[32]]
    sel:      INPUT[Logic[3]]
    out:      OUTPUT[Logic[32]]
    
    def build(self, io):
        inst = Inst(io.inst)
        imms = Array[5, 32]([
                    inst.imm_i(),
                    inst.imm_s(),
                    inst.imm_u(),
                    inst.imm_b(),
                    inst.imm_j(),
                ])
        io.out = imms[io.sel]




def immediate(inst, sel):
    from ctypes import c_int32, c_uint32
    x = int(inst)
    result = 0
    if sel == 0: # I-type
        result = c_int32(x).value >> 20

    elif sel == 1: # S-type
        result = (c_int32(x & 0xfe000000).value >> 20) | ((x & 0xf80) >> 7)

    elif sel == 2: # U-type
        result = c_int32(x & 0xfffff000).value

    elif sel == 3: # B-type
        val = (x & 0x80000000) | ((x & 0x80) << 23) | ((x & 0x7e000000) >> 1) | ((x & 0xf00) << 12)
        result = c_int32(val).value >> 19

    elif sel == 4: # J-type
        val = (x & 0x80000000) | ((x & 0xff000) << 11) | ((x & 0x100000) << 2) | ((x & 0x7fe00000) >> 9)
        result = c_int32(val).value >> 11
    else:
        result = 0
    return c_uint32(result).value


def hex32(x):
    return hex(x)[2:].zfill(8)


def test_inst():
    inst_test = InstTest()
    inst_test.compile()
    print(inst_test.mlir())
    print(inst_test.verilog())

    imms = ["imm_i", "imm_s", "imm_u", "imm_b", "imm_j"]

    with Simulator(inst_test.module, inst_test.name) as sim:
        io = sim.io
        for i in range(80):
            inst = randrange(0, 0xffffffff)
            io.inst = inst
            io.sel = i % 5
            sim.step()

            print(imms[i % 5], hex32(io.out), hex32(immediate(inst, i % 5)), io.out == immediate(inst, i % 5))
            assert io.out == immediate(inst, i % 5)


if __name__ == "__main__":
    test_inst()
