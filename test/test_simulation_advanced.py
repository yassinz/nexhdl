"""
Advanced simulation test for NexHDL simulator.
"""

from nexhdl import *
import os

# --- Module Definitions ---

class Point(Struct):
    x: Logic[16]
    y: Logic[16]

class Frame(Struct):
    points: Array[4, Point]
    valid: Logic[1]

class VideoProcessor(Module):
    frame_in:  INPUT[Frame]
    frame_out: OUTPUT[Frame]
    
    def build(self, io):
        # Simply pass through the frame, but we'll modify it in the test and check values
        io.frame_out = io.frame_in

class Matrix(Module):
    rows: INPUT[Array[2, Array[2, Logic[8]]]]
    out:  OUTPUT[Logic[8]]
    
    def build(self, io):
        # out = rows[0][0] + rows[1][1]
        io.out = io.rows[0][0] + io.rows[1][1]

# --- Test Functions ---

def test_nested_struct_array():
    print("\n=== Testing Nested Struct/Array Simulation ===")
    m = VideoProcessor()
    m.compile()
    
    with m.simulate() as sim:
        # Create a sample frame using nested dicts and lists
        sample_frame = {
            'points': [
                {'x': 10, 'y': 20},
                {'x': 30, 'y': 40},
                {'x': 50, 'y': 60},
                {'x': 70, 'y': 80}
            ],
            'valid': 1
        }
        
        sim.io.frame_in = sample_frame
        sim.step()
        
        output_frame = sim.io.frame_out
        
        print(f"Input frame:  {sample_frame}")
        print(f"Output frame: {output_frame}")
        
        # Verify correctness
        assert output_frame == sample_frame
        assert output_frame['points'][0]['y'] == 20
        assert output_frame['points'][1]['y'] == 40
        assert output_frame['points'][2]['x'] == 50
        assert output_frame['points'][3]['x'] == 70
        assert output_frame['valid'] == 1
    
    print("✓ Nested Struct/Array test passed!")

def test_multi_dim_array():
    print("\n=== Testing Multi-dimensional Array Simulation ===")
    m = Matrix()
    m.compile()
    
    with m.simulate() as sim:
        # 2x2 matrix: [[1, 2], [3, 4]]
        matrix_data = [
            [1, 2],
            [3, 4]
        ]
        
        sim.io.rows = matrix_data
        sim.step()
        
        # Expected: 1 + 4 = 5
        result = sim.io.out
        print(f"Matrix: {matrix_data} -> Sum of diagonals: {result}")
        
        assert result == 5
    
    print("✓ Multi-dimensional Array test passed!")

def test_vcd_advanced():
    print("\n=== Testing VCD for Advanced Types ===")
    m = VideoProcessor()
    m.compile()
    
    vcd_path = "advanced_trace.vcd"
    if os.path.exists(vcd_path):
        os.remove(vcd_path)
        
    with m.simulate() as sim:
        sim.vcd(vcd_path)
        for i in range(4):
            frame = {
                'points': [{'x': i*10 + j, 'y': i*20 + j} for j in range(4)],
                'valid': i % 2
            }
            sim.io.frame_in = frame
            sim.step()
    
    print(f"VCD file created: {vcd_path}")
    
    # Check VCD header for hierarchy
    with open(vcd_path, 'r') as f:
        header = f.read(2000) # Read first 2KB
        
    print("VCD signals (header snippet):")
    # Look for scope definitions
    scopes = [line for line in header.split('\n') if '$scope' in line or '$var' in line and ('points' in line or 'x' in line)]
    for s in scopes[:15]:
        print(f"  {s}")
        
    assert "$scope module frame_in" in header
    assert "$scope module points" in header
    assert "$scope module [0]" in header
    assert "x" in header
    
    os.remove(vcd_path)
    print("✓ VCD Advanced test passed!")

if __name__ == "__main__":
    try:
        test_nested_struct_array()
        test_multi_dim_array()
        test_vcd_advanced()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    print("\n" + "="*40)
    print("All advanced simulation tests passed! ✓")
