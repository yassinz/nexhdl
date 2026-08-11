from nexhdl import *



# Define a 2D coordinate structure
class Coord[W: int](Struct):
    x: Logic[W]
    y: Logic[W]
    
    def __add__(self, other):
        return Coord[W](x=self.x + other.x, y=self.y + other.y)

# Define sprite state with position and velocity
class SpriteState[W: int](Struct):
    pos: Coord[W]      # Current position
    vel: Coord[W]      # Velocity (can be negative)
    color: Logic[3]    # RGB color (1 bit per channel)


class BouncingSprite[WIDTH: int, SCREEN_W: int, SCREEN_H: int](Module):
    """
    A hardware sprite that bounces around the screen!
    Updates position every clock cycle and reverses direction at boundaries.
    """
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    enable:   INPUT[Logic[1]]
    init_vel: INPUT[Coord[WIDTH]]   # Initial velocity
    pos:      OUTPUT[Coord[WIDTH]]  # Current position
    color:    OUTPUT[Logic[3]]      # Current color
    bounce:   OUTPUT[Logic[1]]      # Pulses high when sprite bounces
    
    def build(self, io):
        # State registers
        sprite = Reg[SpriteState[WIDTH]](init=SpriteState[WIDTH](
            pos=Coord[WIDTH](x=SCREEN_W // 2, y=SCREEN_H // 2),
            vel=Coord[WIDTH](x=2, y=3),
            color=0b101  # Magenta
        ))
        
        # Check boundaries (using hardware comparisons)
        hit_left   = sprite.pos.x == 0
        hit_right  = sprite.pos.x >= (SCREEN_W - 1)
        hit_top    = sprite.pos.y == 0
        hit_bottom = sprite.pos.y >= (SCREEN_H - 1)
        
        # Any bounce event
        any_bounce = hit_left | hit_right | hit_top | hit_bottom
        
        # Calculate new velocity (reverse direction on collision)
        new_vel_x = Mux[Logic[WIDTH]](
            hit_left | hit_right,
            ~sprite.vel.x + 1,  # Two's complement negation
            sprite.vel.x
        )
        
        new_vel_y = Mux[Logic[WIDTH]](
            hit_top | hit_bottom,
            ~sprite.vel.y + 1,  # Two's complement negation
            sprite.vel.y
        )
        
        new_vel = Coord[WIDTH](x=new_vel_x, y=new_vel_y)
        
        # Calculate new position (add velocity)
        new_pos = sprite.pos + new_vel
        
        # Cycle colors on bounce (for fun visual effect!)
        new_color = Mux[Logic[3]](
            any_bounce,
            sprite.color + 1,  # Cycle through 8 colors
            sprite.color
        )
        
        # Update state on clock edge
        with io.clk.posedge, io.rst.negedge:
            sprite.next = Mux[SpriteState[WIDTH]](
                io.enable,
                SpriteState[WIDTH](
                    pos=new_pos,
                    vel=new_vel,
                    color=new_color
                ),
                sprite  # Hold current state if disabled
            )
        
        # Output current state
        io.pos = sprite.pos
        io.color = sprite.color
        io.bounce = any_bounce


# Bonus: Multi-sprite system!
class SpriteField[N_SPRITES: int, WIDTH: int, SCREEN_W: int, SCREEN_H: int](Module):
    """Multiple sprites bouncing around - spatial generation in action!"""
    clk:       INPUT[Clock]
    rst:       INPUT[Reset]
    enable:    INPUT[Logic[1]]
    positions: OUTPUT[Array[N_SPRITES, Coord[WIDTH]]]
    colors:    OUTPUT[Array[N_SPRITES, Logic[3]]]
    
    def build(self, io):
        # Spatially generate N_SPRITES instances in parallel!
        sprites = [
            BouncingSprite[WIDTH, SCREEN_W, SCREEN_H](
                clk=io.clk,
                rst=io.rst,
                enable=io.enable,
                init_vel=Coord[WIDTH](x=i+1, y=(N_SPRITES-i))  # Different velocities
            )
            for i in range(N_SPRITES)
        ]
        
        # Collect outputs into arrays (spatial aggregation)
        io.positions = Array[N_SPRITES, Coord[WIDTH]]([s.pos for s in sprites])
        io.colors = Array[N_SPRITES, Logic[3]]([s.color for s in sprites])


# Simulation: Watch the sprite bounce!
if __name__ == "__main__":
    print("🎮 Retro Sprite Engine Simulation 🎮\n")
    
    # Create a single sprite on a 64x48 screen
    dut = BouncingSprite[8, 64, 48]()
    
    with dut.simulate() as sim:
        # Reset
        sim.io.rst = 0
        sim.io.enable = 1
        sim.io.init_vel = {"x": 2, "y": 3}
        sim.tick()
        sim.io.rst = 1
        
        # Run for 100 cycles and track the bouncing
        print("Cycle | X  | Y  | Color | Bounce")
        print("------|----|----|-------|-------")
        
        for cycle in range(50):
            sim.tick()
            pos = sim.io.pos
            color = sim.io.color
            bounce = "💥" if sim.io.bounce else "  "
            # Print every cycle
            print(f"{cycle:5} | {pos['x']:2} | {pos['y']:2} | {color:3b}   | {bounce}")
            
        
        print("\n✨ Sprite bounced around the screen!")
        print(f"Final position: ({sim.io.pos['x']}, {sim.io.pos['y']})")
    

    # Now simulate a field of 4 sprites!
    print("\n" + "="*50)
    print("🌟 Multi-Sprite Field (4 sprites) 🌟\n")
    # N_SPRITES, WIDTH, SCREEN_W, SCREEN_H
    field = SpriteField[4, 8, 64, 48]()
    
    with field.simulate() as sim:
        sim.io.rst = 0
        sim.io.enable = 1
        sim.tick()
        sim.io.rst = 1
        
        # Run for 30 cycles
        print("Cycle | Sprite Positions (x,y)")
        print("------|" + "-"*40)
        
        for cycle in range(30):
            sim.tick()
            positions = sim.io.positions
            
            if cycle % 5 == 0:
                pos_str = " | ".join([f"({pos['x']:2},{pos['y']:2})" for pos in positions])
                print(f"{cycle:5} | {pos_str}")
        
        print("\n🎨 All sprites are bouncing independently!")

