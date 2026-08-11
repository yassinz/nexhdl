from nexhdl import *

class Rule30[WIDTH: int](Module):
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    seed_en:  INPUT[Logic[1]]        # Load initial state
    seed_val: INPUT[Array[WIDTH, Logic[1]]]
    
    # Current state of the automaton
    state_out: OUTPUT[Array[WIDTH, Logic[1]]]

    def build(self, io):
        # 1. State: The array of cells
        cells = Reg[Array[WIDTH, Logic[1]]](init=Array[WIDTH, Logic[1]]([0]*WIDTH))

        # 2. Spatial Logic: Generate the Rule 30 gates for every cell in parallel
        # Rule 30 logic: Next = Left ^ (Center | Right)
        next_gen = [0] * WIDTH
        
        for i in range(WIDTH):
            # Neighborhood with wrap-around (circular boundary)
            left   = cells[(i - 1) % WIDTH]
            center = cells[i]
            right  = cells[(i + 1) % WIDTH]
            
            # Hardware XOR and OR gates
            next_gen[i] = left ^ (center | right)

        # 3. Temporal Logic: Update state on clock edge
        with io.clk.posedge, io.rst.negedge:
            # If seed_en is high, load seed_val; otherwise, evolve to next_gen
            cells.next = Mux[Array[WIDTH, Logic[1]]](
                io.seed_en, 
                io.seed_val, 
                Array[WIDTH, Logic[1]](next_gen)
            )

        io.state_out = cells

# --- Simulation & Visualization ---
if __name__ == "__main__":
    WIDTH = 31
    dut = Rule30[WIDTH]()
        
    with dut.simulate() as sim:
        # Reset the system
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        
        # Seed: Single '1' in the middle of the array
        initial_pattern = [0] * WIDTH
        initial_pattern[WIDTH // 2] = 1
        
        sim.io.seed_en = 1
        sim.io.seed_val = initial_pattern
        sim.tick() 
        
        # Run for 15 generations and print to console
        sim.io.seed_en = 0
        print("--- Rule 30 Evolution ---")
        for _ in range(16):
            # Convert Array of Logic[1] to a string for visualization
            line = "".join(["█" if bit else " " for bit in sim.io.state_out])
            print(line)
            sim.tick()