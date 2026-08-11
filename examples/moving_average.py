from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Array, Param, clog2

# Validator for power of 2 window sizes to make division easy (shifts)
PowerOf2 = Param[int](lambda x: x > 1 and (x & (x - 1)) == 0, "Window size must be a power of 2 > 1")

class MovingAverage[WINDOW: PowerOf2, WIDTH: int](Module):
    """
    A Moving Average Filter with a parameterized window size.
    Demonstrates using Reg[Array] for a delay line and shift-based division.
    """
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    data_in:  INPUT[Logic[WIDTH]]
    data_out: OUTPUT[Logic[WIDTH]]

    def build(self, io):
        # Create a delay line (shift register) using a Reg of an Array
        # Note: Reg[Array] is a single state element holding the entire array.
        history = Reg[Array[WINDOW, Logic[WIDTH]]]()

        # To compute the sum, we'll keep track of it in a register for efficiency
        # The sum needs more bits to avoid overflow: WIDTH + clog2(WINDOW)
        sum_reg = Reg[Logic[WIDTH + clog2(WINDOW)]]()

        with io.clk.posedge, io.rst.negedge:
            # Shift the delay line: [new_data, hist[0], hist[1], ..., hist[N-2]]
            new_history = [io.data_in] + [history[i] for i in range(WINDOW - 1)]
            history.next = Array[WINDOW, Logic[WIDTH]](new_history)

            # Update the sum: sum = sum + new_data - oldest_data
            oldest_data = history[WINDOW - 1]
            sum_reg.next = sum_reg + io.data_in.zext(sum_reg.width) - oldest_data.zext(sum_reg.width)

        # Average is sum >> log2(WINDOW)
        shift_amount = clog2(WINDOW)
        io.data_out = (sum_reg >> shift_amount).trunc(WIDTH)

if __name__ == "__main__":
    # 4-sample moving average for 16-bit data
    filter_module = MovingAverage[4, 16]()
    
    with filter_module.simulate() as sim:
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1

        samples = [100, 200, 300, 400, 500, 600]
        print(f"Feeding samples: {samples}")
        
        for s in samples:
            sim.io.data_in = s
            sim.tick()
            print(f"Input: {s:3}, Output: {sim.io.data_out:3}")
