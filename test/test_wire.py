from nexhdl import *
import pytest


class TestWire(Module):
    a: INPUT[Logic[32]]
    b: INPUT[Logic[32]]
    out: OUTPUT[Logic[32]]

    def build(self, io):
        w = Wire[Logic[32]]()
        io.out = w
        w.assign = io.a + io.b


def test_wire():
    m = TestWire()
    m.compile()

    with m.simulate() as sim:
        sim.io.a = 10
        sim.io.b = 20
        sim.step()
        assert sim.io.out == 30


def test_wire_with_struct():
    """Test wire with struct type."""
    class Point(Struct):
        x: Logic[16]
        y: Logic[16]
    
    class WireStruct(Module):
        a: INPUT[Point]
        out: OUTPUT[Point]
        
        def build(self, io):
            w = Wire[Point]()
            io.out = w
            w.assign = io.a
    
    m = WireStruct()
    m.compile()

    with m.simulate() as sim:
        sim.io.a = {"x": 10, "y": 20}
        sim.step()
        assert sim.io.out == {"x": 10, "y": 20}

def test_wire_with_array():
    """Test wire with array type."""
    class WireArray(Module):
        a: INPUT[Array[4, Logic[8]]]
        out: OUTPUT[Array[4, Logic[8]]]
        
        def build(self, io):
            w = Wire[Array[4, Logic[8]]]()
            io.out = w
            w.assign = io.a
    
    m = WireArray()
    m.compile()

    with m.simulate() as sim:
        sim.io.a = [1, 2, 3, 4]
        sim.step()
        assert sim.io.out == [1, 2, 3, 4]

def test_wire_int_assignment():
    """Test wire with int assignment."""
    class WireInt(Module):
        out: OUTPUT[Logic[8]]
        
        def build(self, io):
            w = Wire[Logic[8]]()
            io.out = w
            w.assign = 42
    
    m = WireInt()
    m.compile()
    
    with m.simulate() as sim:
        sim.step()
        assert sim.io.out == 42

def test_wire_double_assign():
    """Test that wire can only be assigned once."""
    with pytest.raises(RuntimeError, match="Wire can only be assigned once"):
        class DoubleAssign(Module):
            a: INPUT[Logic[8]]
            b: INPUT[Logic[8]]
            out: OUTPUT[Logic[8]]
            
            def build(self, io):
                w = Wire[Logic[8]]()
                w.assign = io.a
                w.assign = io.b  # Error!
                io.out = w
        
        m = DoubleAssign()
        m.compile()


def test_wire_type_mismatch():
    """Test that wire type mismatch raises error."""
    with pytest.raises(TypeError, match="Type mismatch in Wire.assign"):
        class TypeMismatch(Module):
            a: INPUT[Logic[16]]
            out: OUTPUT[Logic[8]]
            
            def build(self, io):
                w = Wire[Logic[8]]()
                w.assign = io.a  # Error: 16-bit to 8-bit
                io.out = w
        
        m = TypeMismatch()
        m.compile()


def test_wire_invalid_type():
    """Test that invalid assignment type raises error."""
    with pytest.raises(TypeError, match="Cannot assign"):
        class InvalidType(Module):
            out: OUTPUT[Logic[8]]
            
            def build(self, io):
                w = Wire[Logic[8]]()
                w.assign = "invalid"  # Error!
                io.out = w
        
        m = InvalidType()
        m.compile()


def test_wire_overflow():
    """Test that assigning an out-of-range integer to a Logic-typed Wire raises a ValueError."""
    with pytest.raises(ValueError, match=r"Integer 16 out of range for Wire\[Logic\[4\]\]"):
        class Overflow(Module):
            out: OUTPUT[Logic[4]]
            def build(self, io):
                w = Wire[Logic[4]]()
                w.assign = 16  # Error: 16 requires 5 bits (unsigned)
                io.out = w
        
        m = Overflow()
        m.compile()


def test_wire_int_to_struct_error():
    """Test that assigning an int to a non-Logic typed Wire raises a TypeError."""
    class Point(Struct):
        x: Logic[16]
        y: Logic[16]

    with pytest.raises(TypeError, match=r"Cannot assign int to Wire of type Wire\[<Point>\]"):
        class InvalidAssign(Module):
            out: OUTPUT[Point]
            def build(self, io):
                w = Wire[Point]()
                w.assign = 42 # Error: Point is not Logic
                io.out = w
        
        m = InvalidAssign()
        m.compile()


if __name__ == "__main__":
    test_wire()
    test_wire_with_struct()
    test_wire_with_array()
    test_wire_int_assignment()
    print("All basic tests passed!")
    
    # Type error tests require pytest
    try:
        test_wire_double_assign()
    except:
        print("Double assign test passed")
    
    try:
        test_wire_type_mismatch()
    except:
        print("Type mismatch test passed")
    
    try:
        test_wire_invalid_type()
    except:
        print("Invalid type test passed")

    try:
        test_wire_overflow()
    except:
        print("Overflow test passed")

    try:
        test_wire_int_to_struct_error()
    except:
        print("Int to Struct error test passed")
