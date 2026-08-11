import pytest
from nexhdl import Module, INPUT, OUTPUT, Logic, Struct, clog2



def test_param_expression_ports():
    """Test that expressions like W + 1 work in port definitions."""
    class Test[W](Module):
        a: INPUT[W + 1]
        b: INPUT[W]
        out: OUTPUT[W]
        
        def build(self, io):
            io.out = (io.a + io.b.zext(W + 1)).trunc(W)
            
    dut = Test[8]()
    with dut.simulate() as sim:
        sim.io.a = 10
        sim.io.b = 20
        sim.step()
        assert sim.io.out == 30

def test_clog2_in_ports():
    """Test that clog2 function works in port definitions."""
    class TestClog2[W](Module):
        addr: INPUT[clog2(W)]
        out: OUTPUT[8]
        
        def build(self, io):
            io.out = Logic[8](42)
            
    dut = TestClog2[16]() # clog2(16) = 4
    with dut.simulate() as sim:
        sim.io.addr = 15
        sim.step()
        assert sim.io.out == 42
        # Check internal width
        assert dut.hw_module.entry_block.arguments[0].type.width == 4

def test_unparameterized_generic_error():
    """Test that using a generic type without parameters gives a clear error."""
    class Coord[W](Struct):
        x: Logic[W]
        y: Logic[W]
        
    # This should raise a TypeError with a clear message
    with pytest.raises(TypeError, match="Cannot use generic type Coord without parameters"):
        class Text(Module):
            a: INPUT[Coord]
            out: OUTPUT[8]
            
            def build(self, io):
                io.out = Logic[8](0)

def test_parameterized_struct_port():
    """Test that parameterized structs work as port types."""
    class Coord[W](Struct):
        x: Logic[W]
        y: Logic[W]
        
    class Text[W](Module):
        a: INPUT[Coord[W]]
        out: OUTPUT[Coord[W]]
        
        def build(self, io):
            io.out = io.a
            
    dut = Text[16]()
    with dut.simulate() as sim:
        sim.io.a = {"x": 100, "y": 200}
        sim.step()
        assert sim.io.out == {"x": 100, "y": 200}

def test_nested_parameterized_array_port():
    """Test that parameterized arrays of parameterized logic work."""
    from nexhdl import Array
    class TestNested[N, W](Module):
        arr: INPUT[Array[N, Logic[W]]]
        out: OUTPUT[Logic[W]]
        
        def build(self, io):
            io.out = io.arr[0]
            
    dut = TestNested[4, 16]()
    with dut.simulate() as sim:
        sim.io.arr = [1, 2, 3, 4]
        sim.step()
        assert sim.io.out == 1
    
    # Check MLIR/IR types
    from circt.dialects import hw
    ir_type = hw.ArrayType(dut.hw_module.entry_block.arguments[0].type)
    assert ir_type.size == 4
    assert ir_type.element_type.width == 16

def test_complex_expressions_in_ports():
    """Test very complex nested expressions in port bit-widths."""
    class TestComplex[W](Module):
        # (W * 2) + 4
        a: INPUT[W * 2 + 4]
        out: OUTPUT[8]
        
        def build(self, io):
            io.out = Logic[8](0)
            
    dut = TestComplex[10]() # 10 * 2 + 4 = 24
    dut.compile()
    assert dut.hw_module.entry_block.arguments[0].type.width == 24

def test_unparameterized_generic_union_error():
    """Test that using a generic Union without parameters gives a clear error."""
    from nexhdl import Union as NexHDLUnion
    class U[W](NexHDLUnion):
        a: Logic[W]
        b: Logic[W]
        
    with pytest.raises(TypeError, match="Cannot use generic type U without parameters"):
        class Text(Module):
            i: INPUT[U]
            def build(self, io): pass

def test_parameter_resolution_in_nested_struct():
    """Test that parameters resolve correctly when a struct using them is used in a port."""
    class Inner[W](Struct):
        data: Logic[W]
        
    class Outer[W](Module):
        # Pass W through to Inner
        inp: INPUT[Inner[W]]
        out: OUTPUT[Logic[W]]
        
        def build(self, io):
            io.out = io.inp.data
            
    dut = Outer[32]()
    with dut.simulate() as sim:
        sim.io.inp = {"data": 0xDEADBEEF}
        sim.step()
        assert sim.io.out == 0xDEADBEEF

def test_more_param_ops():
    """Test new arithmetic and bitwise operators in parameters."""
    class TestOps[W, N](Module):
        # 2**W + (1 << N)
        # For W=4, N=8: 16 + 256 = 272
        a: INPUT[2**W + (1 << N)]
        out: OUTPUT[8]
        
        def build(self, io):
            io.out = Logic[8](0)
            
    dut = TestOps[4, 8]()
    dut.compile()
    # 2**4 = 16
    # 1 << 8 = 256
    # 16 + 256 = 272
    assert dut.hw_module.entry_block.arguments[0].type.width == 272

def test_invert_op():
    """Test bitwise invert in parameters."""
    class TestInvert[W](Module):
        # ~W
        a: INPUT[~W]
        out: OUTPUT[8]
        def build(self, io): io.out = Logic[8](0)
        
    # ~(-33) = 32
    dut = TestInvert[-33]()
    dut.compile()
    assert dut.hw_module.entry_block.arguments[0].type.width == 32


if __name__ == "__main__":
    test_param_expression_ports()
    test_clog2_in_ports()
    test_unparameterized_generic_error()
    test_parameterized_struct_port()
    test_nested_parameterized_array_port()
    test_complex_expressions_in_ports()
    test_unparameterized_generic_union_error()
    test_parameter_resolution_in_nested_struct()
    test_more_param_ops()
    test_invert_op()
