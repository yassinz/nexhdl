"""
Test serialization of complex types in the simulator.
"""

from nexhdl import *
from circt.ir import Module


# Test module with complex nested type:
# struct<data: array<8 x struct<x: i8, y: i8>>>
mlir_complex = """
module {
    hw.module @"ComplexIO"(
        in %sel : i1, 
        in %val0 : !hw.struct<data: !hw.array<8xstruct<x: i8, y: i8>>>, 
        in %val1 : !hw.struct<data: !hw.array<8xstruct<x: i8, y: i8>>>, 
        out out0 : !hw.struct<data: !hw.array<8xstruct<x: i8, y: i8>>>,
        out out1 : i8
    ) {
        %0 = comb.mux %sel, %val0, %val1 : !hw.struct<data: !hw.array<8xstruct<x: i8, y: i8>>>
        %data = hw.struct_extract %val0["data"] : !hw.struct<data: !hw.array<8xstruct<x: i8, y: i8>>>
        %c7_i3 = hw.constant 7 : i3
        %elem0 = hw.array_get %data[%c7_i3] : !hw.array<8xstruct<x: i8, y: i8>>, i3
        %x = hw.struct_extract %elem0["x"] : !hw.struct<x: i8, y: i8>
        hw.output %0, %x : !hw.struct<data: !hw.array<8xstruct<x: i8, y: i8>>>, i8
    }
}
"""

# Simple test with just array
mlir_array = """
module {
    hw.module @"ArrayIO"(
        in %arr_in : !hw.array<4xi8>,
        out arr_out : !hw.array<4xi8>,
        out sum : i8
    ) {
        %c0 = hw.constant 0 : i2
        %c1 = hw.constant 1 : i2
        %c2 = hw.constant 2 : i2
        %c3 = hw.constant 3 : i2
        %a = hw.array_get %arr_in[%c0] : !hw.array<4xi8>, i2
        %b = hw.array_get %arr_in[%c1] : !hw.array<4xi8>, i2
        %c = hw.array_get %arr_in[%c2] : !hw.array<4xi8>, i2
        %d = hw.array_get %arr_in[%c3] : !hw.array<4xi8>, i2
        %s1 = comb.add %a, %b : i8
        %s2 = comb.add %s1, %c : i8
        %s3 = comb.add %s2, %d : i8
        hw.output %arr_in, %s3 : !hw.array<4xi8>, i8
    }
}
"""

# Simple test with just struct
mlir_struct = """
module {
    hw.module @"StructIO"(
        in %point : !hw.struct<x: i16, y: i16>,
        out point_out : !hw.struct<x: i16, y: i16>,
        out sum : i16
    ) {
        %x = hw.struct_extract %point["x"] : !hw.struct<x: i16, y: i16>
        %y = hw.struct_extract %point["y"] : !hw.struct<x: i16, y: i16>
        %s = comb.add %x, %y : i16
        hw.output %point, %s : !hw.struct<x: i16, y: i16>, i16
    }
}
"""


def test_array_io():
    """Test array input/output with list syntax."""
    print("\n=== Testing Array IO ===")
    m = Module.parse(mlir_array)
    
    with Simulator(m, "ArrayIO") as sim:
        io = sim.io
        
        # Write array as list
        io.arr_in = [10, 20, 30, 40]
        sim.step()
        
        # Read array as list
        arr_out = io.arr_out
        sum_out = io.sum
        
        print(f"Input:  [10, 20, 30, 40]")
        print(f"Output: {arr_out}")
        print(f"Sum:    {sum_out} (expected: 100)")
        
        assert arr_out == [10, 20, 30, 40], f"Array mismatch: {arr_out}"
        assert sum_out == 100, f"Sum mismatch: {sum_out}"
    
    print("✓ Array IO test passed!")


def test_struct_io():
    """Test struct input/output with dict syntax."""
    print("\n=== Testing Struct IO ===")
    m = Module.parse(mlir_struct)
    
    with Simulator(m, "StructIO") as sim:
        io = sim.io
        
        # Write struct as dict
        io.point = {'x': 100, 'y': 200}
        sim.step()
        
        # Read struct as dict
        point_out = io.point_out
        sum_out = io.sum
        
        print(f"Input:  {{'x': 100, 'y': 200}}")
        print(f"Output: {point_out}")
        print(f"Sum:    {sum_out} (expected: 300)")
        
        assert point_out == {'x': 100, 'y': 200}, f"Struct mismatch: {point_out}"
        assert sum_out == 300, f"Sum mismatch: {sum_out}"
    
    print("✓ Struct IO test passed!")


def test_nested_complex_io():
    """Test nested struct with array of structs."""
    print("\n=== Testing Nested Complex IO ===")
    m = Module.parse(mlir_complex)
    
    with Simulator(m, "ComplexIO") as sim:
        io = sim.io
        
        # Build complex nested structure:
        # struct { data: array of 8 struct { x: i8, y: i8 } }
        val0_data = [{'x': i, 'y': i * 2} for i in range(8)]
        val1_data = [{'x': 100 + i, 'y': 200 + i} for i in range(8)]
        
        io.sel = 1
        io.val0 = {'data': val0_data}
        io.val1 = {'data': val1_data}
        sim.step()
        
        out0 = io.out0
        out1 = io.out1  # Should be val0.data[0].x = 0
        
        print(f"val0: {{'data': {val0_data[:2]}...}}")
        print(f"val1: {{'data': {val1_data[:2]}...}}")
        print(f"sel:  1 (select val0)")
        print(f"out0: {{'data': {out0['data'][:2]}...}}")
        print(f"out1 (val0.data[0].x): {out1} (expected: 0)")
        
        # When sel=1, output should be val0
        assert out0 == {'data': val0_data}, f"Complex struct mismatch"
        assert out1 == 0, f"Extracted x mismatch: {out1}"
        
        # Try sel=0, should get val1
        io.sel = 0
        sim.step()
        out0 = io.out0
        out1 = io.out1  # Still val0.data[0].x since extraction is from val0
        
        print(f"\nsel:  0 (select val1)")
        print(f"out0: {{'data': {out0['data'][:2]}...}}")
        
        assert out0 == {'data': val1_data}, f"Complex struct mismatch when sel=0"
    
    print("✓ Nested Complex IO test passed!")


def test_backwards_compat():
    """Test that simple int assignment still works for simple ports."""
    print("\n=== Testing Backwards Compatibility ===")
    m = Module.parse(mlir_array)
    
    with Simulator(m, "ArrayIO") as sim:
        io = sim.io
        
        # The sum output is i8, should work as int
        io.arr_in = [1, 2, 3, 4]
        sim.step()
        
        sum_val = io.sum
        assert isinstance(sum_val, int), f"Expected int, got {type(sum_val)}"
        assert sum_val == 10, f"Sum mismatch: {sum_val}"
    
    print("✓ Backwards compatibility test passed!")


def test_vcd_complex_types():
    """Test VCD tracing with complex types (arrays, structs)."""
    print("\n=== Testing VCD Complex Types ===")
    import os
    
    m = Module.parse(mlir_struct)
    vcd_file = "/tmp/test_complex_vcd.vcd"
    
    with Simulator(m, "StructIO") as sim:
        # Start VCD tracing
        sim.vcd(vcd_file)
        
        # Run a few cycles with different values
        for i in range(5):
            sim.io.point = {'x': i * 10, 'y': i * 20}
            sim.step()
        
        sim.tracer.stop()
    
    # Verify VCD file was created and has content
    assert os.path.exists(vcd_file), "VCD file not created"
    
    with open(vcd_file, 'r') as f:
        vcd_content = f.read()
    
    # Check for hierarchical structure
    print("VCD file created. Checking content...")
    print("-" * 40)
    
    # Print header portion for inspection
    lines = vcd_content.split('\n')
    for line in lines[:30]:
        print(line)
    print("..." if len(lines) > 30 else "")
    print("-" * 40)
    
    # Verify expected structure
    assert "$scope module StructIO" in vcd_content, "Missing module scope"
    assert "$scope module point" in vcd_content, "Missing struct scope for 'point'"
    assert "x" in vcd_content, "Missing field 'x'"  
    assert "y" in vcd_content, "Missing field 'y'"
    assert "$upscope" in vcd_content, "Missing upscope"
    
    # Clean up
    os.remove(vcd_file)
    
    print("✓ VCD Complex Types test passed!")


def test_vcd_nested_types():
    """Test VCD with deeply nested types (struct containing array of structs)."""
    print("\n=== Testing VCD Nested Types ===")
    import os
    
    m = Module.parse(mlir_complex)
    vcd_file = "/tmp/test_nested_vcd.vcd"
    
    with Simulator(m, "ComplexIO") as sim:
        sim.vcd(vcd_file)
        
        val0_data = [{'x': i, 'y': i * 2} for i in range(8)]
        sim.io.sel = 1
        sim.io.val0 = {'data': val0_data}
        sim.io.val1 = {'data': [{'x': 0, 'y': 0}] * 8}
        sim.step()
        
        sim.tracer.stop()
    
    with open(vcd_file, 'r') as f:
        vcd_content = f.read()
    
    # Check for nested hierarchy
    print("Nested VCD structure:")
    print("-" * 40)
    lines = vcd_content.split('\n')
    for line in lines[:50]:
        print(line)
    print("..." if len(lines) > 50 else "")
    print("-" * 40)
    
    # Verify nested structure exists
    assert "$scope module val0" in vcd_content, "Missing val0 scope"
    assert "$scope module data" in vcd_content, "Missing data scope"
    assert "[0]" in vcd_content, "Missing array index [0]"
    
    os.remove(vcd_file)
    print("✓ VCD Nested Types test passed!")


if __name__ == "__main__":
    test_array_io()
    test_struct_io()
    test_nested_complex_io()
    test_backwards_compat()
    test_vcd_complex_types()
    test_vcd_nested_types()
    print("\n" + "="*50)
    print("All serialization tests passed! ✓")

