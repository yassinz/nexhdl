from nexhdl import *
from random import randrange
from alu import ALU
from lsu import LSU, RAM
from pc import PC
from reg_file import REG_FILE
from csr import CSR
from inst import Inst

import os

class Core(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]

    # Debug / Visualization Outputs
    inst:  OUTPUT[Logic[32]]
    pc:    OUTPUT[Logic[32]]
    taken: OUTPUT[Logic[1]]

    # MMIO / Debug Ports
    write: OUTPUT[Logic[1]]
    read:  OUTPUT[Logic[1]]
    data:  INPUT[Logic[32]] 

    rs1: OUTPUT[Logic[32]]
    rs2: OUTPUT[Logic[32]]

    alu: OUTPUT[Logic[32]]
    mem: OUTPUT[Logic[32]]
    csr: OUTPUT[Logic[32]]

    def build(self, io):
        # Define the Datapath Bus (All internal signals)
        class Datapath(Struct):
            # State & Fetch
            pc:        Logic[32]
            inst:      Logic[32] # From RAM Port 0
            taken:     Logic[1]
            
            # Execution Inputs
            rs1:       Logic[32]
            rs2:       Logic[32]
            
            # Execution Results
            alu:       Logic[32]
            csr:       Logic[32]
            mem_load:  Logic[32] # LSU Result (to RegFile)
            
            # LSU <-> RAM Interconnect
            lsu_addr:  Logic[32]
            lsu_wdata: Logic[32]
            lsu_we:    Logic[1]
            ram_rdata: Logic[32] # From RAM Port 1

        # Create the bus wire
        dp = Wire[Datapath]()
        
        # Instantiate Modules (Connecting inputs to the wire)
        
        pc = PC[32](
            clk    = io.clk,
            rst    = io.rst,
            rs1    = dp.rs1,
            inst   = dp.inst,
            taken  = dp.taken
        )

        ram = RAM[0x80000](
            clk   = io.clk,
            rst   = io.rst,
            addr0 = pc.out,         # Fetch Address
            addr1 = dp.lsu_addr,    # Data Address
            wdata = dp.lsu_wdata,
            we    = dp.lsu_we
        )
        
        reg_file = REG_FILE[32](
            clk  = io.clk,
            rst  = io.rst,
            inst = dp.inst,
            mem  = dp.mem_load,
            alu  = dp.alu,
            csr  = dp.csr,
            pc   = dp.pc
        )

        alu = ALU[32](
            rs1  = dp.rs1,
            rs2  = dp.rs2,
            inst = dp.inst
        )
        
        lsu = LSU(
            rs1  = dp.rs1,
            rs2  = dp.rs2,
            inst = dp.inst,
            mem_rdata = dp.ram_rdata
        )

        csr = CSR[32](
            clk  = io.clk,
            rst  = io.rst,
            rs1  = dp.rs1,
            inst = dp.inst
        )

        # Top Level IO Assignments & MMIO Logic
        inst = Inst(dp.inst)
        
        # Simple MMIO Address Detection
        store_addr = dp.lsu_addr # We can use the calculated address from LSU!
        
        # For Load address, LSU calculates it internally, but we can replicate 
        # or expose it if needed. For now, let's just peek RS1+Imm
        load_addr = dp.rs1 + inst.imm_i()

        # MMIO Flags (Virtual Address 0x110000)
        io.write = (inst.opcode() == 0b01000) & (store_addr == 0x110000)
        io.read  = (inst.opcode() == 0b00000) & (load_addr == 0x110000)


        # Close the Loop (Assign Module Outputs to Datapath Wire)
        dp.assign = Datapath(
            pc        = pc.out,
            inst      = ram.out0,      # Instruction comes from RAM Port 0
            taken     = alu.taken,
            
            rs1       = reg_file.rs1,
            rs2       = reg_file.rs2,
            
            alu       = alu.out,
            csr       = csr.out,
            mem_load  = Mux[32](io.read, io.data, lsu.out),
            
            lsu_addr  = lsu.mem_addr,
            lsu_wdata = lsu.mem_wdata,
            lsu_we    = lsu.mem_we & (lsu.mem_addr < 0x100000),
            ram_rdata = ram.out1       # Data read comes from RAM Port 1
        )

        
        # Debug
        io.inst  = dp.inst
        io.pc    = dp.pc
        io.taken = dp.taken

        io.rs1 = dp.rs1
        io.rs2 = dp.rs2

        io.alu = dp.alu
        io.mem = dp.mem_load
        io.csr = dp.csr




def test_core():
    core = Core()
    core.compile()

    with core.simulate() as sim:        
        # Read Program
        try:
            with open("examples/RV32I/program/program.bin", "rb") as f:
            #with open("examples/RV32I/micropython.bin", "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell() + 4
                f.seek(0)
                code = [int.from_bytes(f.read(4), 'little') for _ in range(size // 4)]
        except FileNotFoundError as e:
            print("[Sim] Firmware not found!")
            print(e)
            return
        
        # Load Program
        sim.memories['RAM'][:len(code)] = code

        read_data = list("[i for i in range(10)]\n\r\x04")
        
        # Reset
        io = sim.io
        io.rst = 0
        sim.tick()
        io.rst = 1

        # Run
        for i in range(100000):
            if io.write:
                print(chr(io.rs2 & 0xff), end="")
            if io.read:
                io.data = ord(read_data.pop(0))

            sim.tick()

        print("\nDone.")


if __name__ == "__main__":
    test_core()

