from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Array, Param, clog2

class FIRFilter[WIDTH: int, COEFFS: list](Module):
    """
    A Finite Impulse Response (FIR) Filter.
    
    Architecture:
    y[n] = sum(Coeff_i * x[n-i])
    
    Demonstrates:
    1. Reg[Array] for an efficient delay line.
    2. Python-based generation of Multiply-Accumulate chains using a list parameter.
    3. Proper precision handling (widening for internal sums).
    """
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    data_in:  INPUT[Logic[WIDTH]]
    data_out: OUTPUT[Logic[WIDTH]]

    def build(self, io):
        NUM_TAPS = len(COEFFS)
        
        # 1. Delay line (Shift Register)
        # Holds [x[n-1], x[n-2], ..., x[n-N+1]]
        delay_line = Reg[Array[NUM_TAPS - 1, Logic[WIDTH]]]()
        
        with io.clk.posedge, io.rst.negedge:
            # Shift the delay line
            new_delay = [io.data_in] + [delay_line[i] for i in range(NUM_TAPS - 2)]
            delay_line.next = Array[NUM_TAPS - 1, Logic[WIDTH]](new_delay)
            
        # 2. MAC Chain
        # Full precision: WIDTH (data) + 16 (for coeffs) + clog2(NUM_TAPS) (for accumulation)
        acc_width = WIDTH + 16 
        
        # Combine input and delay line for easier iteration: [x[n], x[n-1], ..., x[n-N+1]]
        samples = [io.data_in] + [delay_line[i] for i in range(NUM_TAPS - 1)]
        
        total = Logic[acc_width](0)
        for i in range(NUM_TAPS):
            # Multiply-Accumulate
            prod = samples[i].zext(acc_width) * Logic[acc_width](COEFFS[i])
            total = total + prod
            
        # 3. Output - Normalize by 2^8 (divide by 256) and truncate back to WIDTH
        io.data_out = (total >> 8).trunc(WIDTH)

if __name__ == "__main__":
    print("--- NexHDL FIR Filter Example ---")
    
    # 16-bit FIR filter with moving average coefficients [0.25, 0.25, 0.25, 0.25]
    # Scaled by 256: [64, 64, 64, 64]
    MY_COEFFS = [64, 64, 64, 64]
    fir = FIRFilter[16, MY_COEFFS]()
    print(fir.verilog())
    
    with fir.simulate() as sim:
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1
        
        # Feed a step input
        print("\nStep Response Test:")
        sim.io.data_in = 1000
        for i in range(6):
            sim.tick()
            print(f"Cycle {i}: In=1000, Out={sim.io.data_out}")
            
        # Should ramp up:
        # T0: 1000 * 0.25 = 250
        # T1: (1000 + 1000) * 0.25 = 500
        # T2: (1000 + 1000 + 1000) * 0.25 = 750
        # T3: (1000 + 1000 + 1000 + 1000) * 0.25 = 1000
        # T4: 1000
        
        assert sim.io.data_out > 200 # Sanity check for first cycles
