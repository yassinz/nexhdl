from nexhdl import *
import pytest

class Point[W: int](Struct):
    x: Logic[W]
    y: Logic[W]

class Color(Struct):
    r: Logic[8]
    g: Logic[8]
    b: Logic[8]

def test_struct_field_type_mismatch():
    """Test that Struct fields must match declared types."""
    class TestModule(Module):
        out: OUTPUT[Logic[1]]
        def build(self, io):
            with pytest.raises(TypeError, match="Type mismatch for field 'x'"):
                # Point[16] expects Logic[16]
                Point[16](x=Logic[8](1), y=Logic[16](2))
            io.out = Logic[1](0)
    
    m = TestModule()
    m.compile()

def test_struct_int_overflow():
    """Test that Struct fields check for integer overflow."""
    class TestModule(Module):
        out: OUTPUT[Logic[1]]
        def build(self, io):
            with pytest.raises(ValueError, match="Integer 70000 out of range for field 'x'"):
                Point[16](x=70000, y=0)
            io.out = Logic[1](0)
    
    m = TestModule()
    m.compile()

def test_union_field_type_mismatch():
    """Test that Union fields must match declared types."""
    class MyUnion(Union):
        p: Point[16]
        c: Color

    class TestModule(Module):
        out: OUTPUT[Logic[1]]
        def build(self, io):
            with pytest.raises(TypeError, match="Type mismatch for union field 'p'"):
                # p expects Point[16], we give Color
                MyUnion(p=Color(r=1, g=2, b=3))
            io.out = Logic[1](0)
    
    m = TestModule()
    m.compile()

def test_union_int_overflow():
    """Test that Union fields check for integer overflow."""
    class LocalUnion(Union):
        v: Logic[4]

    class TestModule(Module):
        out: OUTPUT[Logic[1]]
        def build(self, io):
            with pytest.raises(ValueError, match="Integer 16 out of range for union field 'v'"):
                LocalUnion(v=16)
            io.out = Logic[1](0)
    
    m = TestModule()
    m.compile()


def test_array_field_type_mismatch():
    """Test that Array elements must match declared element type."""
    class TestModule(Module):
        out: OUTPUT[Logic[1]]
        def build(self, io):
            with pytest.raises(TypeError, match="Element type mismatch"):
                # Array of Logic[16] cannot take Logic[8]
                Array[2, Logic[16]]([Logic[16](1), Logic[8](2)])
            io.out = Logic[1](0)
    
    m = TestModule()
    m.compile()


def test_array_int_overflow():
    """Test that Array elements check for integer overflow."""
    class TestModule(Module):
        out: OUTPUT[Logic[1]]
        def build(self, io):
            with pytest.raises(ValueError, match="Integer 16 out of range for Array element"):
                Array[4, Logic[4]]([16, 0, 0, 0])
            io.out = Logic[1](0)
    
    m = TestModule()
    m.compile()

if __name__ == "__main__":
    import sys
    pytest.main([__file__])
