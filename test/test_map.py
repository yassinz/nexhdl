#!/usr/bin/env python3

from nexhdl import *


def test_map_basic():
    """Test basic Map creation and lookup."""
    print("=" * 60)
    print("Test: Basic Map")
    print("=" * 60)
    
    class MapTest(Module):
        key: INPUT[Logic[4]]
        out: OUTPUT[Logic[32]]
        
        def build(self, io):
            # Create map with 4 entries
            lookup = Map[4, Logic[32]](
                (Logic[4](0b0001), Logic[32](10)),
                (Logic[4](0b0010), Logic[32](20)),
                (Logic[4](0b0100), Logic[32](30)),
                (Logic[4](0b1000), Logic[32](40)),
            )
            
            io.out = lookup[io.key]
    
    m = MapTest()
    m.compile()
    print(m.verilog())
    print("✓ Basic Map test passed\n")


def test_map_explicit_key_type():
    """Test Map with explicit Logic key type."""
    print("=" * 60)
    print("Test: Map with Explicit Key Type")
    print("=" * 60)
    
    class MapTest(Module):
        key: INPUT[Logic[3]]
        out: OUTPUT[Logic[16]]
        
        def build(self, io):
            # Explicit key type
            lookup = Map[Logic[3], Logic[16]](
                (Logic[3](0b001), Logic[16](100)),
                (Logic[3](0b010), Logic[16](200)),
                (Logic[3](0b100), Logic[16](300)),
            )
            
            io.out = lookup[io.key]
    
    m = MapTest()
    m.compile()
    print(m.verilog())
    print("✓ Explicit key type test passed\n")


def test_map_with_struct():
    """Test Map with struct values."""
    print("=" * 60)
    print("Test: Map with Struct Values")
    print("=" * 60)
    
    class Point(Struct):
        x: Logic[16]
        y: Logic[16]
    
    class MapTest(Module):
        key: INPUT[Logic[2]]
        out: OUTPUT[Point]
        
        def build(self, io):
            lookup = Map[2, Point](
                (Logic[2](0b01), Point(x=Logic[16](10), y=Logic[16](20))),
                (Logic[2](0b10), Point(x=Logic[16](30), y=Logic[16](40))),
            )
            
            io.out = lookup[io.key]
    
    m = MapTest()
    m.compile()
    print(m.verilog())
    print("✓ Struct values test passed\n")


def test_map_with_array():
    """Test Map with array values."""
    print("=" * 60)
    print("Test: Map with Array Values")
    print("=" * 60)
    
    class MapTest(Module):
        key: INPUT[Logic[2]]
        out: OUTPUT[Array[4, Logic[8]]]
        
        def build(self, io):
            lookup = Map[2, Array[4, Logic[8]]](
                (Logic[2](0b01), Array[4, Logic[8]]([1, 2, 3, 4])),
                (Logic[2](0b10), Array[4, Logic[8]]([5, 6, 7, 8])),
            )
            
            io.out = lookup[io.key]
    
    m = MapTest()
    m.compile()
    print(m.verilog())
    print("✓ Array values test passed\n")


def test_map_simulation():
    print("=" * 60)
    print("Test: Map Simulation")
    print("=" * 60)
    
    class TestMap(Module):
        key: INPUT[Logic[4]]
        out: OUTPUT[Logic[32]]
        
        def build(self, io):
            lookup = Map[4, 32](
                (0b0001, 10),
                (0b0010, 71),
                (0b0110, 41),
                (0b1110, 56),
            )

            io.out = lookup[io.key]

    m = TestMap()
    m.compile()
    print("Generated Verilog:")
    print(m.verilog())

    with m.simulate() as sim:
        sim.io.key = 0b1111
        sim.step()
        assert sim.io.out == 0
        sim.io.key = 0b1110
        sim.step()
        assert sim.io.out == 56
        sim.io.key = 0b0110
        sim.step()
        assert sim.io.out == 41
        sim.io.key = 0b0010
        sim.step()
        assert sim.io.out == 71
        sim.io.key = 0b0001
        sim.step()
        assert sim.io.out == 10
        print("✓ Map simulation test passed\n")





def test_map_errors():
    """Test Map error handling."""
    print("=" * 60)
    print("Test: Map Error Handling")
    print("=" * 60)
    
    # Test key width mismatch
    try:
        lookup = Map[4, Logic[32]](
            (Logic[3](0b001), Logic[32](10)),  # Wrong key width
        )
        print("✗ Should have raised key width error")
    except TypeError as e:
        print(f"✓ Key width error: {e}")
    
    # Test value type mismatch
    try:
        lookup = Map[4, Logic[32]](
            (Logic[4](0b0001), Logic[16](10)),  # Wrong value type
        )
        print("✗ Should have raised value type error")
    except TypeError as e:
        print(f"✓ Value type error: {e}")
    
    # Test lookup key width mismatch
    class MapTest(Module):
        key: INPUT[Logic[3]]
        out: OUTPUT[Logic[32]]
        
        def build(self, io):
            lookup = Map[4, Logic[32]](
                (Logic[4](0b0001), Logic[32](10)),
            )
            io.out = lookup[io.key]  # Wrong key width
    
    try:
        m = MapTest()
        m.compile()
        print("✗ Should have raised lookup key width error")
    except TypeError as e:
        print(f"✓ Lookup key width error: {e}")
    
    print()


if __name__ == "__main__":
    test_map_basic()
    test_map_explicit_key_type()
    test_map_with_struct()
    test_map_with_array()
    test_map_simulation()
    test_map_errors()
    print("=" * 60)
    print("All Map tests passed!")
    print("=" * 60)
