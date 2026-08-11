from nexhdl import *
import time
import os

class Counter(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    out: OUTPUT[Logic[32]]

    def build(self, io):
        count = Reg[Logic[32]](init=0)
        with io.clk.posedge, io.rst.negedge:
            count.next = count + 1
        io.out = count

def test_basic_run():
    print("\n--- Test: Basic Run ---")
    dut = Counter()
    with dut.simulate() as sim:
        sim.io.rst = 1; sim.step()
        sim.io.rst = 0; sim.step() # Reset
        sim.io.rst = 1; sim.step()
        
        N = 1000
        sim.run(N)
        print(f"Count after {N}: {sim.io.out}")
        assert sim.io.out == N

def test_sequential_run():
    print("\n--- Test: Sequential Run ---")
    dut = Counter()
    with dut.simulate() as sim:
        sim.io.rst = 1; sim.step()
        sim.io.rst = 0; sim.step()
        sim.io.rst = 1; sim.step()
        
        sim.run(100)
        print(f"Count after 100: {sim.io.out}")
        sim.run(200)
        print(f"Count after 300: {sim.io.out}")
        assert sim.io.out == 300

def test_edge_cases():
    print("\n--- Test: Edge Cases (0 and negative) ---")
    dut = Counter()
    with dut.simulate() as sim:
        sim.io.rst = 1; sim.step()
        sim.io.rst = 0; sim.step()
        sim.io.rst = 1; sim.step()
        
        sim.run(0)
        print(f"Count after run(0): {sim.io.out}")
        assert sim.io.out == 0
        
        sim.run(-10)
        print(f"Count after run(-10): {sim.io.out}")
        assert sim.io.out == 0

def test_manual_clock():
    print("\n--- Test: Manual Clock Name ---")
    dut = Counter()
    with dut.simulate() as sim:
        sim.io.rst = 1; sim.step()
        sim.io.rst = 0; sim.step()
        sim.io.rst = 1; sim.step()
        
        sim.run(50, clk_name="clk")
        print(f"Count after run(50, clk_name='clk'): {sim.io.out}")
        assert sim.io.out == 50

def test_vcd_integration():
    print("\n--- Test: VCD Integration ---")
    dut = Counter()
    vcd_file = "test_run.vcd"
    if os.path.exists(vcd_file): os.remove(vcd_file)
    
    with dut.simulate() as sim:
        sim.vcd(vcd_file)
        sim.io.rst = 1; sim.tick()
        sim.io.rst = 0; sim.tick()
        sim.io.rst = 1; sim.tick()
        
        # Run 100 cycles
        sim.run(100)
        print(f"Time in tracer after run(100): {sim.tracer.time}")
        # Expected time: 3 cycles (tick) * 2 steps + 100 cycles * 2 steps = 206
        # sim.run(N) advances time by (N * 2) - 1 and then writeTimestep() adds 1.
        # Initial 3 ticks: t=1 (falling), t=2 (rising), t=3 (f), t=4 (r), t=5 (f), t=6 (r)
        
    assert os.path.exists(vcd_file)
    if os.path.exists(vcd_file): os.remove(vcd_file)
    print(f"SUCCESS: VCD generated.")

if __name__ == "__main__":
    try:
        test_basic_run()
        test_sequential_run()
        test_edge_cases()
        test_manual_clock()
        test_vcd_integration()
        print("\nALL RUN TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
