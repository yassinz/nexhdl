from nexhdl import *

# 1. Define a Struct for our Game Status (Reference Sec 2)
# Layout: [Jackpot (1 bit) | Sum (5 bits)]
class Status(Struct):
    is_jackpot: Logic[1]
    total_score: Logic[5]

class LuckySevenSlot(Module):
    # IO Definitions (Reference Sec 1)
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    pull:   INPUT[Logic[1]]              # High = Spin, Low = Stop
    reels:  OUTPUT[Array[3, Logic[3]]]   # 3 Reels, values 0-7
    stats:  OUTPUT[Status]               # Structured status output

    def build(self, io):
        # --- State Definitions (Reference Sec 3) ---
        # Three registers initialized to 0, 1, 2 so they start offset
        r1 = Reg[Logic[3]](reset_value=0)
        r2 = Reg[Logic[3]](reset_value=1)
        r3 = Reg[Logic[3]](reset_value=2)
        
        # A speed controller to make reels spin at different rates
        # Reel 1: Every tick, Reel 2: Every 2 ticks, Reel 3: Every 4 ticks
        ticker = Reg[Logic[2]]()

        # --- Logic (Reference Sec 4 & 7) ---
        
        # 1. Calculate Next States using Mux (Strict Hardware Logic)
        # Note: Logic[3] naturally wraps 7 -> 0 on overflow
        
        # Reel 1: Spins every cycle if pulling
        r1_next = Mux[3](io.pull, r1 + 1, r1)
        
        # Reel 2: Spins if pulling AND ticker LSB is 1 (every 2nd cycle)
        r2_next = Mux[3](io.pull & ticker[0], r2 + 1, r2)
        
        # Reel 3: Spins if pulling AND ticker is 11 (every 4th cycle)
        r3_next = Mux[3](io.pull & (ticker == 3), r3 + 1, r3)

        # 2. Win Condition Logic
        # We need three 7s. 7 in binary is 111.
        is_winner = (r1 == 7) & (r2 == 7) & (r3 == 7)
        
        # 3. Calculate Score (Math adds width, so we cast to Logic[5])
        # We use .zext() to match widths before adding, just to be safe/explicit
        current_sum = r1.zext(5) + r2.zext(5) + r3.zext(5)

        # --- Temporal Updates (Reference Sec 5) ---
        with io.clk.posedge, io.rst.negedge:
            ticker.next = ticker + 1
            r1.next = r1_next
            r2.next = r2_next
            r3.next = r3_next

        # --- Output Assignments (Reference Sec 1) ---
        # Construct the Array
        io.reels = Array[3, Logic[3]]([r1, r2, r3])
        
        # Construct the Struct
        io.stats = Status(
            is_jackpot=is_winner,
            total_score=current_sum
        )

# --- Simulation (Reference Sec 12) ---
if __name__ == "__main__":
    dut = LuckySevenSlot()

    with dut.simulate() as sim:
        print("🎰 Initializing Lucky 7 Slot Machine...")
        
        # Reset sequence
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        
        # Pull the lever! (Spin for 20 cycles)
        sim.io.pull = 1

        # Spin for a number of cycles
        TRY_YOUR_LUCK = 55    # Hint: It's a scam
        for _ in range(TRY_YOUR_LUCK):
            sim.tick()
            
        # Let go of the lever (Stop)
        sim.io.pull = 0
        sim.tick()
        
        # Read the results
        res = sim.io.reels
        stats = sim.io.stats # This comes out as a dict for Structs
        
        print(f"Reels Stopped at: {res} (Raw: {res[0]}, {res[1]}, {res[2]})")
        print(f"Score: {stats['total_score']}")
        
        if stats['is_jackpot']:
            print("🚨 JACKPOT! 🚨")
        else:
            print("💸 Better luck next time.")