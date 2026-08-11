from nexhdl import *

# --- Struct Definitions ---
class RGBColor(Struct):
    r: Logic[8]
    g: Logic[8]
    b: Logic[8]

# --- The DVD Logo Physics Engine ---
class DVDLogoEngine(Module):
    # Inputs
    clk:        INPUT[Clock]
    rst:        INPUT[Reset]
    frame_tick: INPUT[Logic[1]]   # Pulsed once per frame update (~60Hz)
    pixel_x:    INPUT[Logic[10]]  # Current VGA scanout X position (0..639)
    pixel_y:    INPUT[Logic[10]]  # Current VGA scanout Y position (0..479)
    
    # Outputs
    rgb:        OUTPUT[RGBColor]   # RGB Output for the current pixel
    bounces:    OUTPUT[Logic[16]]  # Total bounce counter output

    def build(self, io):
        # Hardware Constants (640x480 resolution, 64x32 Logo size)
        SCREEN_W = 640
        SCREEN_H = 480
        LOGO_W   = 64
        LOGO_H   = 32

        # -------------------------------------------------------------
        # 1. Hardware State Registers
        # -------------------------------------------------------------
        pos_x      = Reg[Logic[10]]() # X position
        pos_y      = Reg[Logic[10]]() # Y position
        dir_x      = Reg[Logic[1]]()  # 0 = Right, 1 = Left
        dir_y      = Reg[Logic[1]]()  # 0 = Down, 1 = Up
        color_idx  = Reg[Logic[2]]()  # Color selection index (0..3)
        bounce_cnt = Reg[Logic[16]]() # Total screen bounce counter

        # -------------------------------------------------------------
        # 2. Boundary Collision Logic (Combinational)
        # -------------------------------------------------------------
        max_x = Logic[10](SCREEN_W - LOGO_W)
        max_y = Logic[10](SCREEN_H - LOGO_H)

        # Compare current positions with screen borders (Produces 1-bit hardware signals)
        hit_right  = pos_x >= max_x
        hit_left   = pos_x == Logic[10](0)
        hit_bottom = pos_y >= max_y
        hit_top    = pos_y == Logic[10](0)

        # Hit signal flags using hardware OR (|) operator
        hit_x   = hit_right | hit_left
        hit_y   = hit_bottom | hit_top
        any_hit = hit_x | hit_y

        # Determine next directions based on collision state
        next_dir_x = Mux[Logic[1]](hit_right, Logic[1](1),
                     Mux[Logic[1]](hit_left,  Logic[1](0), dir_x))

        next_dir_y = Mux[Logic[1]](hit_bottom, Logic[1](1),
                     Mux[Logic[1]](hit_top,    Logic[1](0), dir_y))

        # Calculate next positions (+1 or -1 based on direction)
        step_x = Mux[Logic[10]](next_dir_x, pos_x - Logic[10](1), pos_x + Logic[10](1))
        step_y = Mux[Logic[10]](next_dir_y, pos_y - Logic[10](1), pos_y + Logic[10](1))

        # -------------------------------------------------------------
        # 3. Sequential Update Logic (Clock Context)
        # -------------------------------------------------------------
        with io.clk.posedge, io.rst.negedge:
            # Update positions and directions only when frame_tick is active
            pos_x.next     = Mux[Logic[10]](io.frame_tick, step_x, pos_x)
            pos_y.next     = Mux[Logic[10]](io.frame_tick, step_y, pos_y)
            dir_x.next     = Mux[Logic[1]](io.frame_tick, next_dir_x, dir_x)
            dir_y.next     = Mux[Logic[1]](io.frame_tick, next_dir_y, dir_y)

            # Cycle color on wall collision
            color_idx.next = Mux[Logic[2]](io.frame_tick & any_hit, color_idx + Logic[2](1), color_idx)

            # Increment bounce register on wall collision
            bounce_cnt.next = Mux[Logic[16]](io.frame_tick & any_hit, bounce_cnt + Logic[16](1), bounce_cnt)

        # -------------------------------------------------------------
        # 4. Color Palette Lookup Table (Hardware LUT)
        # -------------------------------------------------------------
        palette = Map[Logic[2], RGBColor](
            (Logic[2](0), RGBColor(r=Logic[8](0),   g=Logic[8](255), b=Logic[8](255))), # Cyan
            (Logic[2](1), RGBColor(r=Logic[8](255), g=Logic[8](0),   b=Logic[8](255))), # Magenta
            (Logic[2](2), RGBColor(r=Logic[8](255), g=Logic[8](255), b=Logic[8](0))),   # Yellow
            default=RGBColor(r=Logic[8](50), g=Logic[8](255), b=Logic[8](50))           # Neon Green
        )
        active_color = palette[color_idx]

        # -------------------------------------------------------------
        # 5. Pixel Scanout Rendering Logic
        # -------------------------------------------------------------
        # Check if the requested beam coordinate (pixel_x, pixel_y) is inside the logo bounding box
        in_x = (io.pixel_x >= pos_x) & (io.pixel_x < (pos_x + Logic[10](LOGO_W)))
        in_y = (io.pixel_y >= pos_y) & (io.pixel_y < (pos_y + Logic[10](LOGO_H)))
        inside_logo = in_x & in_y

        black = RGBColor(r=Logic[8](0), g=Logic[8](0), b=Logic[8](0))

        # Connect Final IO outputs
        io.rgb     = Mux[RGBColor](inside_logo, active_color, black)
        io.bounces = bounce_cnt


# =====================================================================
# 🧪 Simulation & Interactive Visualizer
# =====================================================================
if __name__ == "__main__":
    dut = DVDLogoEngine()
    print(dut.verilog())  # Print the generated Verilog code for inspection
    
    print("🚀 Initializing DVD Logo Physics Engine Simulation...\n")

    with dut.simulate() as sim:
        # Reset Cycle
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        sim.io.frame_tick = 1
        sim.io.pixel_x = 0
        sim.io.pixel_y = 0

        # Fast-Forward Simulation & track Bounces
        last_bounce_count = -1

        for frame in range(1200):  # Simulate 1200 animation steps
            sim.tick()
            
            current_bounces = sim.io.bounces
            if current_bounces != last_bounce_count:
                print(f"💥 BOUNCE DETECTED! Frame: {frame:4d} | Total Bounces: {current_bounces}")
                last_bounce_count = current_bounces

        print("\n🎨 Sampling Pixel Rendering Engine at Screen Center...")
        # Point VGA beam to current animated position
        sim.io.pixel_x = 576  # Right edge area
        sim.io.pixel_y = 10
        print(f"Rendered RGB at (576, 10): {sim.io.rgb}")



