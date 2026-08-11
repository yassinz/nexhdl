from nexhdl import *
from inst import Inst



class RAM[SIZE](Module):
    # Input
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    we:     INPUT[Logic[1]]
    wdata:  INPUT[Logic[32]]
    addr0:  INPUT[Logic[32]]
    addr1:  INPUT[Logic[32]]
    # Output
    out0:   OUTPUT[Logic[32]]
    out1:   OUTPUT[Logic[32]]

    def build(self, io):
        mem = Mem[SIZE, Logic[32]](name="RAM")
        
        with io.clk.posedge, io.rst.negedge:
            mem.write(io.addr1[2:clog2(SIZE)+2], io.wdata, io.we)

        io.out0 = mem[io.addr0[2:clog2(SIZE)+2]]
        io.out1 = mem[io.addr1[2:clog2(SIZE)+2]]


class LSU(Module):
    # Input
    rs1:       INPUT[Logic[32]]
    rs2:       INPUT[Logic[32]]
    inst:      INPUT[Logic[32]]
    mem_rdata: INPUT[Logic[32]]
    # Output
    out:       OUTPUT[Logic[32]]
    mem_addr:  OUTPUT[Logic[32]]
    mem_wdata: OUTPUT[Logic[32]]
    mem_we:    OUTPUT[Logic[1]]

    def build(self, io):
        inst = Inst(io.inst)
        op = inst.funct3()

        # Address
        addr = io.rs1 + Mux[32](inst.opcode() == 0b01000, inst.imm_s(), inst.imm_i())
        
        # Alignment
        shift = addr[0:2].zext(32) << 3

        # Store Logic
        base_mask = Array[4, Logic[32]]([0xFF, 0xFFFF, 0xFFFFFFFF, 0])[op[0:2]]
        full_mask = base_mask << shift
        io.mem_wdata = (io.mem_rdata & ~full_mask) | ((io.rs2 << shift) & full_mask)
        io.mem_addr  = addr
        io.mem_we    = (inst.opcode() == 0b01000)

        # Load Logic
        aligned = io.mem_rdata >> shift
        io.out = Array[8, Logic[32]]([
            aligned[0:8].sext(32),  # LB
            aligned[0:16].sext(32), # LH
            aligned,                # LW
            0,
            aligned[0:8].zext(32),  # LBU
            aligned[0:16].zext(32), # LHU
            0, 0
        ])[op]


class System[RAM_SIZE](Module):
    # Input
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    rs1:      INPUT[Logic[32]]
    rs2:      INPUT[Logic[32]]
    inst:     INPUT[Logic[32]]
    # Output
    load_out: OUTPUT[Logic[32]]

    def build(self, io):
        lsu_addr = Wire[Logic[32]]()
        lsu_wdata = Wire[Logic[32]]()
        lsu_we = Wire[Logic[1]]()
        ram_rdata = Wire[Logic[32]]()

        ram = RAM[RAM_SIZE](
            clk    = io.clk,
            rst    = io.rst,
            addr0  = Logic[32](0),
            addr1  = lsu_addr,
            wdata  = lsu_wdata,
            we     = lsu_we
        )
        lsu = LSU(
            rs1    = io.rs1,
            rs2    = io.rs2,
            inst   = io.inst,
            mem_rdata = ram_rdata
        )

        lsu_addr.assign = lsu.mem_addr
        lsu_wdata.assign = lsu.mem_wdata
        lsu_we.assign = lsu.mem_we
        ram_rdata.assign = ram.out1

        io.load_out = lsu.out




def hex32(val): return format(val, '08x')

def test_data(data, offset):
    """
    Calculates expected results. 
    Updated to support unaligned shifting (byte granularity) to match the LSU hardware.
    """
    # Shift the whole word down by the byte offset (0, 8, 16, or 24 bits)
    val_shifted = data >> (offset * 8)
    
    # Extract raw values
    byte_val = val_shifted & 0xFF
    half_val = val_shifted & 0xFFFF
    word_val = val_shifted & 0xFFFFFFFF # Python needs mask

    # Sign Extension Helper
    def sext(v, width):
        sign_bit = 1 << (width - 1)
        return (v - (1 << width)) if (v & sign_bit) else v

    # Python integers are arbitrary precision, mask back to 32-bit unsigned for comparison
    return {
        "LB":  sext(byte_val, 8) & 0xFFFFFFFF,
        "LH":  sext(half_val, 16) & 0xFFFFFFFF,
        "LW":  word_val,
        "LBU": byte_val,
        "LHU": half_val
    }

def test_lsu():
    # Instantiate the System (Wrapper for LSU + RAM)
    sys = System[0x1000]() # 4KB RAM
    
    with sys.simulate() as sim:
        io = sim.io
        io.rst = 1; sim.tick(); io.rst = 0

        # Data to load
        data_list = [0x12345678, 0xaabbccdd, 0x44556677, 0x9abcdeff]
        sim.memories["RAM"][:4] = data_list
        
        for i in range(16): # Check first 16 bytes (4 words)
            word_idx = i // 4
            offset   = i % 4
            word_val = data_list[word_idx]
            
            expected = test_data(word_val, offset)
            
            # Setup inputs
            io.rs1 = i # Byte Address
            
            # Helper to run check
            def check(funct3, name):
                io.inst = 0x00000003 | (funct3 << 12)
                sim.tick()
                
                # Check result
                assert io.load_out == expected[name], \
                    f"Addr {i} ({name}): Expected {hex32(expected[name])}, Got {hex32(io.load_out)}"
            
            print(f"Testing Addr {i} (Offset {offset})...", end="")
            
            check(0b000, "LB")
            check(0b001, "LH")
            check(0b010, "LW")
            check(0b100, "LBU")
            check(0b101, "LHU")
            
            print(" OK")


if __name__ == "__main__":
    test_lsu()