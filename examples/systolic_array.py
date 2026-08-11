from nexhdl import Module, INPUT, OUTPUT, Logic, Array, Clock, Reset, Reg, Param, Mux




class ProcessingElement[WIDTH: int](Module):
    """
    A single Processing Element (PE) for a systolic array.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    en:     INPUT[Logic[1]]
    
    in_a:   INPUT[Logic[WIDTH]]
    in_b:   INPUT[Logic[WIDTH]]
    
    out_a:  OUTPUT[Logic[WIDTH]]
    out_b:  OUTPUT[Logic[WIDTH]]
    acc:    OUTPUT[Logic[WIDTH * 2]]

    def build(self, io):
        # Accumulator and buffers for shifting data
        a_reg   = Reg[Logic[WIDTH]]()
        b_reg   = Reg[Logic[WIDTH]]()
        acc_reg = Reg[Logic[WIDTH * 2]]()

        with io.clk.posedge, io.rst.negedge:
            # We use Mux for hardware-native conditional logic
            a_reg.next = Mux[Logic[WIDTH]](io.en, io.in_a, a_reg)
            b_reg.next = Mux[Logic[WIDTH]](io.en, io.in_b, b_reg)
                
            # Perform Multiply-Accumulate
            prod = io.in_a.zext(WIDTH * 2) * io.in_b.zext(WIDTH * 2)
            acc_reg.next = Mux[Logic[WIDTH * 2]](io.en, acc_reg + prod, acc_reg)
        
        io.out_a = a_reg
        io.out_b = b_reg
        io.acc   = acc_reg


# 1. Define Validators for the Architecture
PositiveInt = Param[int](lambda x: x > 0, "Dimension must be positive")
StandardWidth = Param[int](lambda x: 1 <= x <= 64, "Bit width must be between 1 and 64")


class SystolicArray[ROWS: PositiveInt, COLS: PositiveInt, WIDTH: StandardWidth](Module):
    """
    A 2D Systolic Array for Matrix Multiplication.
    Uses 'Param' validators to ensure valid hardware configuration.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    en:     INPUT[Logic[1]]
    
    # Inputs for the edges of the array
    a_in:   INPUT[Array[ROWS, Logic[WIDTH]]]
    b_in:   INPUT[Array[COLS, Logic[WIDTH]]]
    
    # Final results (Internal accumulators of all PEs)
    results: OUTPUT[Array[ROWS, Array[COLS, Logic[WIDTH * 2]]]]

    def build(self, io):
        # 2D Grid to store PE outputs for wiring
        # Note: We use nested lists in Python to manage the hardware graph
        pe_grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        
        for r in range(ROWS):
            for c in range(COLS):
                # Determine inputs for this PE
                # Left-edge PEs follow io.a_in, others follow neighbors' out_a
                sig_a = io.a_in[r] if c == 0 else pe_grid[r][c-1].out_a
                
                # Top-edge PEs follow io.b_in, others follow neighbors' out_b
                sig_b = io.b_in[c] if r == 0 else pe_grid[r-1][c].out_b
                
                # Instantiate and connect PE
                pe = ProcessingElement[WIDTH](
                    clk  = io.clk,
                    rst  = io.rst,
                    en   = io.en,
                    in_a = sig_a,
                    in_b = sig_b
                )
                pe_grid[r][c] = pe

        # Gather all accumulator outputs into the final 2D array
        res_matrix = []
        for r in range(ROWS):
            row_data = [pe_grid[r][c].acc for c in range(COLS)]
            res_matrix.append(Array[COLS, Logic[WIDTH * 2]](row_data))
            
        io.results = Array[ROWS, Array[COLS, Logic[WIDTH * 2]]](res_matrix)

if __name__ == "__main__":
    # 2x2 Systolic Array with 8-bit inputs
    ROWS, COLS, WIDTH = 2, 2, 8
    
    print("--- NexHDL Parameter Validation Test ---")
    try:
        # Invalid: Negative dimensions
        bad_array = SystolicArray[0, 2, 8]()
    except ValueError as e:
        print(f"✓ Caught invalid dimension: {e}")
        
    try:
        # Invalid: Width too large
        bad_array = SystolicArray[2, 2, 128]()
    except ValueError as e:
        print(f"✓ Caught invalid width: {e}")
    
    print("\n--- Starting Valid 2x2 Systolic Array Simulation ---")
    array = SystolicArray[ROWS, COLS, WIDTH]()
    print(array.verilog())
    
    with array.simulate() as sim:
        sim.io.rst = 0 # Active reset
        sim.tick()
        sim.io.rst = 1 # Release reset
        sim.io.en  = 1
        
        # To perform:
        # A = [[1, 2],    B = [[5, 6],
        #      [3, 4]]         [7, 8]]
        #
        # Systolic timing (staggered inputs):
        # T1: a[0]=1, b[0]=5
        # T2: a[0]=2, a[1]=3, b[0]=7, b[1]=6
        # T3: a[1]=4, b[1]=8
        
        def run_step(a0, a1, b0, b1, step_name):
            sim.io.a_in = [a0, a1]
            sim.io.b_in = [b0, b1]
            sim.tick()
            print(f"Step {step_name}: A_in={sim.io.a_in}, B_in={sim.io.b_in}")
            print(f"  PE[0][0] Acc: {sim.io.results[0][0]}")

        run_step(1, 0, 5, 0, "T1")
        run_step(2, 3, 7, 6, "T2")
        run_step(0, 4, 0, 8, "T3")
        
        # Extra cycles for data to finish propagating
        run_step(0, 0, 0, 0, "T4")
        run_step(0, 0, 0, 0, "T5")
        
        print("\nFinal Result Matrix:")
        for r in range(ROWS):
            print(f"  Row {r}: {sim.io.results[r]}")
            
        # Check C[0][0] = 1*5 + 2*7 = 19
        # Check C[0][1] = 1*6 + 2*8 = 22
        # Check C[1][0] = 3*5 + 4*7 = 43
        # Check C[1][1] = 3*6 + 4*8 = 50
        assert sim.io.results[0][0] == 19
        assert sim.io.results[0][1] == 22
        assert sim.io.results[1][0] == 43
        assert sim.io.results[1][1] == 50
        
        print("\n✓ Matrix Multiplication Successful!")
