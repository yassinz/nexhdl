from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Map, Mux

class State():
    RED    = 0
    GREEN  = 1
    YELLOW = 2

class TrafficLight(Module):
    """
    A simple Traffic Light FSM.
    RED -> GREEN -> YELLOW -> RED
    Transitions occur when 'timer_expired' is high.
    """
    clk:           INPUT[Clock]
    rst:           INPUT[Reset]
    timer_expired: INPUT[Logic[1]]
    
    red_led:    OUTPUT[Logic[1]]
    green_led:  OUTPUT[Logic[1]]
    yellow_led: OUTPUT[Logic[1]]

    def build(self, io):
        # Constants for state encoding
        GREEN  = Logic[2](0)
        YELLOW = Logic[2](1)
        RED    = Logic[2](2)

        # Register to hold the current state
        state = Reg[Logic[2]](reset_value=RED)

        with io.clk.posedge, io.rst.negedge:
            # Define next state transitions using Map or if/else
            # Map is often cleaner for state transitions
            next_state = Map[2, Logic[2]](
                (RED,    Mux[Logic[2]](io.timer_expired, GREEN,  RED)),
                (GREEN,  Mux[Logic[2]](io.timer_expired, YELLOW, GREEN)),
                (YELLOW, Mux[Logic[2]](io.timer_expired, RED,    YELLOW)),
                default=RED
            )[state]
            
            state.next = next_state

        # Decode state to outputs
        io.red_led    = (state == RED)
        io.green_led  = (state == GREEN)
        io.yellow_led = (state == YELLOW)

if __name__ == "__main__":
    dut = TrafficLight()
    
    with dut.simulate() as sim:
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1
        
        def print_status(step_name):
            color = "RED" if sim.io.red_led else "GREEN" if sim.io.green_led else "YELLOW"
            print(f"[{step_name}] Light is: {color}")

        print_status("Start")
        
        # Stay RED for a while
        sim.io.timer_expired = 0
        sim.tick()
        print_status("After 1 tick (timer=0)")
        
        # Trigger transition to GREEN
        sim.io.timer_expired = 1
        sim.tick()
        print_status("After transition (timer=1)")
        
        # Stay GREEN
        sim.io.timer_expired = 0
        sim.tick()
        print_status("After 1 tick (timer=0)")

        # Trigger transition to YELLOW
        sim.io.timer_expired = 1
        sim.tick()
        print_status("After transition (timer=1)")

        # Trigger transition to RED
        sim.io.timer_expired = 1
        sim.tick()
        print_status("After transition (timer=1)")
