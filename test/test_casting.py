from nexhdl import *


# ==============================================================================
# Nested Types for Testing
# ==============================================================================

class Point(Struct):
    x: Logic[16]
    y: Logic[16]

class ArrayOfPoints(Struct):
    # Total width: 2 * 32 = 64 bits
    data: Array[2, Point]

class Packet(Struct):
    # Total: 16 + 32 = 48 bits
    header: Logic[16]
    payload: Array[4, Logic[8]]

# ==============================================================================
# Casting Test Module
# ==============================================================================

class GenericCaster(Module):
    # Inputs (Generic Integers)
    in_u64: INPUT[Logic[64]]
    in_u48: INPUT[Logic[48]]
    
    # Outputs (Complex Nested Types)
    out_points:  OUTPUT[ArrayOfPoints]
    out_packet:  OUTPUT[Packet]
    
    # Roundtrip Outputs (Back to Integers)
    out_u64_rt: OUTPUT[Logic[64]]
    out_u48_rt: OUTPUT[Logic[48]]

    def build(self, io):
        # 1. Cast Logic[64] -> Struct[Array[Struct]]
        # Logic[64] -> ArrayOfPoints
        points = ArrayOfPoints(io.in_u64)
        io.out_points = points
        
        # Roundtrip check: Cast back to Logic[64]
        io.out_u64_rt = Logic[64](points)

        # 2. Cast Logic[48] -> Struct[Logic, Array[Logic]]
        # Logic[48] -> Packet
        packet = Packet(io.in_u48)
        io.out_packet = packet
        
        # Roundtrip check
        io.out_u48_rt = Logic[48](packet)

def test_nested_casting():
    print("\n=== Test Nested Type Casting ===")
    m = GenericCaster()
    m.compile()
    
    with m.simulate() as sim:
        # Test 1: Array of Structs (64 bits)
        # Point = {x:16, y:16}
        # Array = [Point, Point]
        # Layout depends on packing. Usually Array[0] is at LSB.
        val64 = 0x1111222233334444
        sim.io.in_u64 = val64
        
        # Test 2: Mixed Struct (48 bits)
        # Packet = {header:16, payload:32}
        val48 = 0xAABBCCDDEEFF
        sim.io.in_u48 = val48
        
        sim.step()
        
        # Verify Roundtrips
        print(f"U64 Input:     {hex(val64)}")
        print(f"U64 Roundtrip: {hex(sim.io.out_u64_rt)}")
        assert sim.io.out_u64_rt == val64
        
        print(f"U48 Input:     {hex(val48)}")
        print(f"U48 Roundtrip: {hex(sim.io.out_u48_rt)}")
        assert sim.io.out_u48_rt == val48

        print("Nested casting verification successful.")

if __name__ == "__main__":
    try:
        test_nested_casting()
    except Exception as e:
        print(f"\nFAILURE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
