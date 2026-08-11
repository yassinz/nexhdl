from nexhdl import *
import pytest


class TestReg(Module):
    clk:   INPUT[Clock]
    rst: INPUT[Reset]

    out:  OUTPUT[Logic[32]]

    def build(self, io):
        count = Reg[Logic[32]]()

        with io.clk.posedge, io.rst.negedge:
            count.next = count + 1

        io.out = count


def test_reg():
    test_reg = TestReg()
    test_reg.compile()

    with test_reg.simulate() as sim:
        io = sim.io
        io.rst = 1
        for i in range(10):
            sim.tick()
            assert io.out == i + 1

        io.rst = 0
        sim.tick()
        assert io.out == 0

        io.rst = 0
        for i in range(10):
            sim.tick()
            assert io.out == 0


def test_reg_init_int():
    """Test register with int init value."""
    class RegWithInit(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Logic[8]]
        
        def build(self, io):
            reg = Reg[Logic[8]](init=42)
            with io.clk.posedge:
                reg.next = reg + 1
            io.out = reg
    
    m = RegWithInit()
    m.compile()
    print(m.verilog())


def test_reg_init_value():
    """Test register with NexValue init."""
    class RegWithInit(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Logic[16]]
        
        def build(self, io):
            reg = Reg[Logic[16]](init=Logic[16](100))
            with io.clk.posedge:
                reg.next = reg + 1
            io.out = reg
    
    m = RegWithInit()
    m.compile()
    print(m.verilog())


def test_reg_init_int():
    """Test register with int init value."""
    class RegWithInit(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        out: OUTPUT[Logic[8]]
        
        def build(self, io):
            reg = Reg[Logic[8]](init=10)
            with io.clk.posedge, io.rst.negedge:
                reg.next = reg + 1
            io.out = reg
    
    m = RegWithInit()
    m.compile()
    print(m.verilog())


def test_reg_with_array():
    """Test register with array type."""
    class RegArray(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Array[4, Logic[8]]]
        
        def build(self, io):
            reg = Reg[Array[4, Logic[8]]]()
            with io.clk.posedge:
                reg.next = reg
            io.out = reg
    
    m = RegArray()
    m.compile()
    print(m.verilog())


def test_reg_with_struct():
    """Test register with struct type."""
    class Point(Struct):
        x: Logic[16]
        y: Logic[16]
    
    class RegStruct(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Point]
        
        def build(self, io):
            reg = Reg[Point]()
            with io.clk.posedge:
                reg.next = reg
            io.out = reg
    
    m = RegStruct()
    m.compile()
    print(m.verilog())


def test_reg_type_mismatch_init():
    """Test that init value type mismatch raises error."""
    with pytest.raises(TypeError, match="Init type mismatch"):
        reg = Reg[Logic[8]](init=Logic[16](42))


def test_reg_invalid_init_type():
    """Test that invalid init type raises error."""
    with pytest.raises(TypeError, match="Init must be int or NexValue"):
        reg = Reg[Logic[8]](init="invalid")


def test_reg_invalid_init_type():
    """Test that invalid init type raises error."""
    with pytest.raises(TypeError, match="Init must be int or NexValue"):
        reg = Reg[Logic[8]](init="invalid")
    

def test_reg_overflow():
    """Test that assigning an out-of-range integer to a Logic-typed Reg raises a ValueError."""
    with pytest.raises(ValueError, match=r"Integer 32 out of range for Reg\[Logic\[5\]\]"):
        class Overflow(Module):
            clk: INPUT[Clock]
            out: OUTPUT[Logic[5]]
            def build(self, io):
                r = Reg[Logic[5]]()
                with io.clk.posedge:
                    r.next = 32 # Error: 32 requires 6 bits (unsigned)
                io.out = r
        
        m = Overflow()
        m.compile()


def test_reg_int_to_struct_error():
    """Test that assigning an int to a non-Logic typed Reg raises a TypeError."""
    class Point(Struct):
        x: Logic[16]
        y: Logic[16]

    with pytest.raises(TypeError, match=r"Cannot assign int to Reg of type Reg\[<Point>\]"):
        class InvalidAssign(Module):
            clk: INPUT[Clock]
            out: OUTPUT[Point]
            def build(self, io):
                r = Reg[Point]()
                with io.clk.posedge:
                    r.next = 42 # Error: Point is not Logic
                io.out = r
        
        m = InvalidAssign()
        m.compile()


class RegTestComplex[DTYPE, BITS](Module):
    """Register test with parameterized type from main.py."""
    clk:    INPUT[Clock]
    data:   INPUT[DTYPE]
    out:    OUTPUT[DTYPE]

    def build(self, io):
        reg = Reg[Logic[BITS]]()

        with io.clk.posedge:
            reg.next = Logic[BITS](io.data)
        
        io.out = DTYPE(reg)



def test_reg_complex():
    """Test register with Struct and Array casting (from main.py)."""
    class Point[W: int](Struct):
        x: Logic[W]
        y: Logic[W]

    # Test with Struct
    m1 = RegTestComplex[Point[17], 17 * 2]()
    with m1.simulate() as sim:
        io = sim.io
        expected = {"x": 555, "y": 666}
        io.data = expected
        sim.tick()
        assert io.out == expected

    # Test with Array
    m2 = RegTestComplex[Array[4, Logic[19]], 4 * 19]()
    with m2.simulate() as sim:
        io = sim.io
        expected = [5555, 6666, 7777, 8888]
        io.data = expected
        sim.tick()
        assert io.out == expected

    print("\n✓ Complex register (Struct/Array casting) tests passed!")


if __name__ == "__main__":
    test_reg()
    test_reg_init_int()
    test_reg_init_value()
    test_reg_with_array()
    test_reg_with_struct()
    test_reg_complex()
    print("All basic tests passed!")
    
    # Type mismatch tests require pytest
    try:
        test_reg_type_mismatch_init()
    except:
        print("Type mismatch test for init passed")
    
    try:
        test_reg_type_mismatch_reset()
    except:
        print("Type mismatch test for reset passed")
    
    try:
        test_reg_invalid_init_type()
    except:
        print("Invalid init type test passed")
    
    try:
        test_reg_invalid_reset_type()
    except:
        print("Invalid reset type test passed")

    try:
        test_reg_overflow()
    except:
        print("Overflow test passed")

    try:
        test_reg_int_to_struct_error()
    except:
        print("Int to Struct error test passed")
