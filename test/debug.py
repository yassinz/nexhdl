from nexhdl import *

# ==============================================================================
# Multi-Context Elastic Processing Element (PE)
# ==============================================================================
class ElasticTile[WIDTH: int, CONTEXT_DEPTH: int](Module):
    """
    A Coarse-Grained Reconfigurable Tile that surpasses LUTs:
    - Word-level arithmetic (No bit-routing overhead)
    - Multi-context execution (Cycle-by-cycle runtime reconfiguration)
    - Elastic streaming (Integrated Ready/Valid backpressure handshaking)
    """
    CTR_BITS = clog2(CONTEXT_DEPTH)

    clk:        INPUT[Clock]
    rst:        INPUT[Reset]

    # Data Stream A & B (Operand inputs with Ready/Valid handshaking)
    data_a:     INPUT[Logic[WIDTH]]
    valid_a:    INPUT[Logic[1]]
    ready_a:    OUTPUT[Logic[1]]

    data_b:     INPUT[Logic[WIDTH]]
    valid_b:    INPUT[Logic[1]]
    ready_b:    OUTPUT[Logic[1]]

    # Downstream consumer backpressure
    downstream_ready: INPUT[Logic[1]]

    # Data Stream Out
    data_out:   OUTPUT[Logic[WIDTH]]
    valid_out:  OUTPUT[Logic[1]]

    # Multi-Context Instruction Memory (Cycle-by-cycle microcode)
    # Opcode format: [ALU_OP(3b) | ACC_EN(1b) | ROUTE_SEL(2b)]
    cfg_insts:  INPUT[Array[CONTEXT_DEPTH, Logic[6]]]
    cfg_limit:  INPUT[Logic[CTR_BITS]]  # Number of active contexts in loop

    def build(self, io):
        # 1. State Registers
        ctx_ptr   = Reg[Logic[self.CTR_BITS]]()
        acc_reg   = Reg[Logic[WIDTH]]()
        out_reg   = Reg[Logic[WIDTH]]()
        valid_reg = Reg[Logic[1]]()

        # 2. Elastic Handshaking Logic
        # Tile can fire if operands are valid and downstream can accept data
        tile_fire = io.valid_a & io.valid_b & (io.downstream_ready | ~valid_reg)
        
        io.ready_a = tile_fire
        io.ready_b = tile_fire
        io.valid_out = valid_reg
        io.data_out = out_reg

        # 3. Dynamic Context Fetch (Fetch instruction for current cycle)
        inst = io.cfg_insts[ctx_ptr]
        alu_op   = inst[3:6]  # 3-bit Opcode
        acc_en   = inst[2:3]  # 1-bit Accumulate Flag
        
        # 4. High-Performance Word-Level ALU
        # Select between input B or Accumulator register
        op_b = Mux[Logic[WIDTH]](acc_en, acc_reg, io.data_b)

        alu_add = io.data_a + op_b
        alu_sub = io.data_a - op_b
        alu_and = io.data_a & op_b
        alu_xor = io.data_a ^ op_b
        alu_sll = io.data_a << op_b
        alu_mul = (io.data_a * op_b).trunc(WIDTH)
        alu_max = Mux[Logic[WIDTH]](io.data_a > op_b, io.data_a, op_b)

        # Dynamic Operation Multiplexer
        alu_res = Map[3, Logic[WIDTH]](
            (Logic[3](0), alu_add),
            (Logic[3](1), alu_sub),
            (Logic[3](2), alu_and),
            (Logic[3](3), alu_xor),
            (Logic[3](4), alu_sll),
            (Logic[3](5), alu_mul),
            (Logic[3](6), alu_max),
            default=io.data_a
        )[alu_op]

        # 5. Sequential Execution & Context Stepping
        with io.clk.posedge, io.rst.negedge:
            # Advance to next context instruction on execution
            next_ptr = Mux[Logic[self.CTR_BITS]](
                ctx_ptr == io.cfg_limit,
                Logic[self.CTR_BITS](0),
                ctx_ptr + 1
            )
            
            ctx_ptr.next = Mux[Logic[self.CTR_BITS]](tile_fire, next_ptr, ctx_ptr)
            out_reg.next = Mux[Logic[WIDTH]](tile_fire, alu_res, out_reg)
            acc_reg.next = Mux[Logic[WIDTH]](tile_fire, alu_res, acc_reg)
            
            next_valid = Mux[Logic[1]](
                tile_fire,
                Logic[1](1),
                Mux[Logic[1]](io.downstream_ready, Logic[1](0), valid_reg)
            )
            valid_reg.next = next_valid


# ==============================================================================
# Simulation: Multi-Context Dynamic Execution
# ==============================================================================
if __name__ == "__main__":
    # 16-bit Tile with 4 Context Slots
    dut = ElasticTile[16, 4]()
    
    with dut.simulate() as sim:
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        sim.io.downstream_ready = 1
        
        # Program 3 Contexts to cycle through automatically:
        # Context 0: OP 5 (MUL) -> A * B
        # Context 1: OP 0 (ADD) with ACC=1 -> (Previous Result) + A
        # Context 2: OP 6 (MAX) -> MAX(A, B)
        OP_MUL = 0b101_0_00
        OP_MACC = 0b000_1_00
        OP_MAX = 0b110_0_00
        
        sim.io.cfg_insts = [OP_MUL, OP_MACC, OP_MAX, 0]
        sim.io.cfg_limit = 2  # Cycle across contexts 0 -> 1 -> 2 -> 0

        # Cycle 1: Execute Context 0 (MUL): 4 * 5 = 20
        sim.io.valid_a = 1; sim.io.data_a = 4
        sim.io.valid_b = 1; sim.io.data_b = 5
        sim.tick()
        print(f"Cycle 1 [Context 0: MUL]: Output = {sim.io.data_out}") # 20

        # Cycle 2: Execute Context 1 (MACC): (Acc=20) + 10 = 30
        sim.io.data_a = 10
        sim.tick()
        print(f"Cycle 2 [Context 1: MACC]: Output = {sim.io.data_out}") # 30

        # Cycle 3: Execute Context 2 (MAX): MAX(15, 80) = 80
        sim.io.data_a = 15
        sim.io.data_b = 80
        sim.tick()
        print(f"Cycle 3 [Context 2: MAX]: Output = {sim.io.data_out}") # 80