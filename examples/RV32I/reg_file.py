from nexhdl import *
from random import randrange
from inst import Inst





class REG_FILE[WIDTH](Module):
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    inst:     INPUT[Logic[32]]
    mem:      INPUT[Logic[WIDTH]]
    alu:      INPUT[Logic[WIDTH]]
    csr:      INPUT[Logic[WIDTH]]
    pc:       INPUT[Logic[WIDTH]]

    rs1:     OUTPUT[Logic[WIDTH]]
    rs2:     OUTPUT[Logic[WIDTH]]

    def build(self, io):
        inst = Inst(inst=io.inst)
        imm_u = inst.imm_u()
        opcode = inst.opcode()
        rd = inst.rd()

        we = (opcode != 0b11000) & (opcode != 0b01000) & (rd != 0)

        LOAD = io.mem
        ALU = io.alu
        LUI = imm_u
        AUIP = io.pc + imm_u
        JAL = io.pc + 4
        CSR = io.csr

        data_map = Map[5, WIDTH](
            (0b00000, LOAD),
            (0b01100, ALU),
            (0b00100, ALU),
            (0b01101, LUI),
            (0b00101, AUIP),
            (0b11011, JAL),
            (0b11001, JAL),  # JALR
            (0b11100, CSR),
            default=0xffffffff,
        )

        data = data_map[opcode]

        rs1 = inst.rs1()
        rs2 = inst.rs2()

        mem = Mem[32, WIDTH]()

        with io.clk.posedge, io.rst.negedge:
            mem.write(rd, data, we)

        io.rs1 = mem[rs1]
        io.rs2 = mem[rs2]







hex32 = lambda x: format(x, '08x')
bin5 = lambda x: format(x, '05b')

def test_reg_file():
    reg_file = REG_FILE[32]()
    reg_file.compile()
    #print(reg_file.mlir())
    #print(reg_file.verilog())


    with Simulator(reg_file.module, reg_file.name) as sim:
        io = sim.io

        # Write to all registers
        for i in range(32):
            io.inst = eval(f'0b0000000_00000_00000_000_{bin5(i)}_00000_11')
            io.mem = i * 0xffcc
            sim.tick()
        
        # Read from registers
        for i in range(32):
            io.inst = eval(f'0b0000000_{bin5(i)}_{bin5(i)}_000_00000_01000_11')
            sim.tick()
            assert io.rs1 == i * 0xffcc
            assert io.rs2 == i * 0xffcc


        # LOAD operation
        io.inst = 0b0000000_00001_00001_000_00001_00000_11 # LOAD
        io.mem = 0xffaaffee
        sim.tick()
        assert io.rs1 == 0xffaaffee
        assert io.rs2 == 0xffaaffee

        # ALU operation
        io.inst = 0b0000000_00001_00001_000_00001_00100_11 # ALU_I
        io.alu = 0x11223344
        sim.tick()
        assert io.rs1 == 0x11223344
        assert io.rs2 == 0x11223344

        io.inst = 0b0000000_00001_00001_000_00001_01100_11 # ALU
        io.alu = 0xaaaabbbb
        sim.tick()
        assert io.rs1 == 0xaaaabbbb
        assert io.rs2 == 0xaaaabbbb

        # CSR operation
        io.inst = 0b0000000_00001_00001_000_00001_11100_11 # CSR
        io.csr = 0x55667788
        sim.tick()
        assert io.rs1 == 0x55667788
        assert io.rs2 == 0x55667788

        # LUI operation
        io.inst = 0b1000010_10001_10010_101_00001_01101_11 # LUI
        sim.tick()
        io.inst = 0b0000000_00001_00001_000_00001_01000_11
        sim.tick()
        assert io.rs1 == 0x85195000
        assert io.rs2 == 0x85195000

        # AUIPC operation
        io.inst = 0b0000000_00000_00000_001_00001_00101_11 # AUIPC
        io.pc = 0xff0000ff
        sim.tick()
        io.inst = 0b0000000_00001_00001_000_00001_01000_11
        sim.tick()
        assert io.rs1 == 0xff0010ff
        assert io.rs2 == 0xff0010ff
        
        # JAL operation
        io.inst = 0b0000000_00001_00001_000_00001_11011_11 # JAL
        io.pc = 0xcaac3157
        sim.tick()
        assert io.rs1 == 0xcaac3157 + 4
        assert io.rs2 == 0xcaac3157 + 4
        sim.tick()

        # Test R[0] == 0
        io.inst = 0b0000000_00000_00000_000_00000_00000_11
        io.mem = 0xffaaffee
        sim.tick()
        assert io.rs1 == 0
        assert io.rs2 == 0
        



if __name__ == "__main__":
    test_reg_file()