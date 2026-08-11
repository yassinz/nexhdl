import time
from nexhdl import *

class GameOfLife[WIDTH: int, HEIGHT: int](Module):
    # Standard Controls
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    
    # Configuration
    load:   INPUT[Logic[1]]  # 1 = Load Seed, 0 = Run Game
    seed:   INPUT[Array[HEIGHT, Array[WIDTH, Logic[1]]]] # Initial pattern
    
    # Current State Output
    grid:   OUTPUT[Array[HEIGHT, Array[WIDTH, Logic[1]]]]

    def build(self, io):
        # 1. State: The Grid Register
        # We store the entire grid in a Register of Arrays
        current_state = Reg[Array[HEIGHT, Array[WIDTH, Logic[1]]]]()
        
        # 2. Spatial Generation (Python Loops)
        # We generate the "next state" logic for every cell in parallel.
        next_rows = []
        
        for y in range(HEIGHT):
            next_cells = []
            for x in range(WIDTH):
                # --- Elaboration Time Logic (Python) ---
                # Determine neighbor coordinates with wrapping (Toroidal surface)
                # We use python modulo (%) to find the wires connecting edges
                indices = [
                    ((y-1)%HEIGHT, (x-1)%WIDTH), ((y-1)%HEIGHT, x), ((y-1)%HEIGHT, (x+1)%WIDTH),
                    (y,            (x-1)%WIDTH),                    (y,            (x+1)%WIDTH),
                    ((y+1)%HEIGHT, (x-1)%WIDTH), ((y+1)%HEIGHT, x), ((y+1)%HEIGHT, (x+1)%WIDTH)
                ]
                
                # --- Hardware Logic Construction ---
                # 1. Get current cell status (1 bit)
                # Note: We access the Register output state
                me = current_state[y][x]
                
                # 2. Sum neighbors. 
                # CRITICAL: Neighbors are 1-bit. To add them, we must Zero-Extend (.zext) 
                # them to 4 bits so the sum doesn't overflow 1 bit.
                neighbor_sum = Logic[4](0)
                for ny, nx in indices:
                    neighbor_sum = neighbor_sum + current_state[ny][nx].zext(4)
                
                # 3. Apply Rules of Life using Logic/Mux (NOT Python if!)
                # Rule 1: 3 neighbors = Birth (or stay alive)
                # Rule 2: 2 neighbors = Stay status quo (Alive stays alive, Dead stays dead)
                # Rule 3: Anything else = Die
                
                # Logic: Is Alive if (Sum == 3) OR (Sum == 2 AND I am Alive)
                # We use hardware comparisons (==) and bitwise operators (&, |)
                birth     = (neighbor_sum == 3)
                survive   = (neighbor_sum == 2) & me
                next_cell = birth | survive
                
                next_cells.append(next_cell)
            
            # Pack the cells into a Row
            next_rows.append(Array[WIDTH, Logic[1]](next_cells))

        # Pack the rows into the full Grid
        next_state_logic = Array[HEIGHT, Array[WIDTH, Logic[1]]](next_rows)

        # 3. Temporal Update
        with io.clk.posedge, io.rst.negedge:
            # If loading, take seed. If running, take calculated next state.
            current_state.next = Mux[Array[HEIGHT, Array[WIDTH, Logic[1]]]](
                io.load,
                io.seed,
                next_state_logic
            )

        # Drive output
        io.grid = current_state

# --- Simulation ---
if __name__ == "__main__":
    W, H = 10, 10
    dut = GameOfLife[W, H]()
    
    with dut.simulate() as sim:
        # 1. Reset
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        
        # 2. Create a "Glider" Pattern (Python list of lists)
        # 0 1 0
        # 0 0 1
        # 1 1 1
        initial_grid = [[0] * W for _ in range(H)]
        initial_grid[0][1] = 1
        initial_grid[1][2] = 1
        initial_grid[2][0] = 1
        initial_grid[2][1] = 1
        initial_grid[2][2] = 1

        # 3. Load the Seed
        sim.io.load = 1
        sim.io.seed = initial_grid
        sim.tick() # Clock edge loads seed into Register
        sim.io.load = 0 # Turn off load mode
        
        # 4. Run Simulation
        print("\n--- Conway's Game of Life (Hardware Sim) ---")
        for frame in range(30):
            # Get current hardware state (list of lists)
            grid_out = sim.io.grid
            
            # Visualization
            print(f"Frame {frame}:")
            print("+" + "-" * (W*2) + "+")
            for row in grid_out:
                line = "".join(["██" if cell else "  " for cell in row])
                print(f"|{line}|")
            print("+" + "-" * (W*2) + "+")
            
            # Step Hardware
            sim.tick()
            time.sleep(0.1) # Just for effect