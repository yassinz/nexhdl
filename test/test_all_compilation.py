"""
Test file for nexhdl2 - verifies the unified type system works.

Run with: python test/test_nexhdl2.py
"""

from nexhdl import *


# ============================================================================
# Test 1: Basic Logic
# ============================================================================

def test_logic():
    print("=" * 60)
    print("Test 1: Basic Logic")
    print("=" * 60)
    
    class Adder(Module):
        a: INPUT[Logic[32]]
        b: INPUT[Logic[32]]
        out: OUTPUT[Logic[32]]
        
        def build(self, io):
            io.out = io.a + io.b
    
    adder = Adder()
    adder.compile()
    print(adder.verilog())
    print("✓ Basic Logic test passed\n")


# ============================================================================
# Test 2: Parameterized Module
# ============================================================================

def test_parameterized():
    print("=" * 60)
    print("Test 2: Parameterized Module")
    print("=" * 60)
    
    class Adder[WIDTH: int](Module):
        a: INPUT[Logic[WIDTH]]
        b: INPUT[Logic[WIDTH]]
        out: OUTPUT[Logic[WIDTH]]
        
        def build(self, io):
            io.out = io.a + io.b
    
    adder16 = Adder[16]()
    adder16.compile()
    print(adder16.verilog())
    print("✓ Parameterized Module test passed\n")


# ============================================================================
# Test 3: Struct
# ============================================================================

def test_struct():
    print("=" * 60)
    print("Test 3: Struct")
    print("=" * 60)
    
    class Point(Struct):
        x: Logic[32]
        y: Logic[32]
    
    class PointAdder(Module):
        a: INPUT[Point]
        b: INPUT[Point]
        out: OUTPUT[Point]
        
        def build(self, io):
            io.out = Point(
                x=io.a.x + io.b.x,
                y=io.a.y + io.b.y
            )
    
    adder = PointAdder()
    adder.compile()
    print(adder.verilog())
    print("✓ Struct test passed\n")


# ============================================================================
# Test 4: Array
# ============================================================================

def test_array():
    print("=" * 60)
    print("Test 4: Array")
    print("=" * 60)
    
    class ArraySum(Module):
        a: INPUT[Array[4, Logic[8]]]
        out: OUTPUT[Logic[8]]
        
        def build(self, io):
            # Sum all elements
            result = io.a[0]
            for i in range(1, 4):
                result = result + io.a[i]
            io.out = result
    
    mod = ArraySum()
    mod.compile()
    print(mod.verilog())
    print("✓ Array test passed\n")


# ============================================================================
# Test 5: Array of Struct
# ============================================================================

def test_array_of_struct():
    print("=" * 60)
    print("Test 5: Array of Struct")
    print("=" * 60)
    
    class Point(Struct):
        x: Logic[16]
        y: Logic[16]
    
    class PointArraySum(Module):
        points: INPUT[Array[4, Point]]
        out: OUTPUT[Point]
        
        def build(self, io):
            x_sum = io.points[0].x
            y_sum = io.points[0].y
            
            for i in range(1, 4):
                x_sum = x_sum + io.points[i].x
                y_sum = y_sum + io.points[i].y
            
            io.out = Point(x=x_sum, y=y_sum)
    
    mod = PointArraySum()
    mod.compile()
    print(mod.verilog())
    print("✓ Array of Struct test passed\n")


# ============================================================================
# Test 6: Nested Array
# ============================================================================

def test_nested_array():
    print("=" * 60)
    print("Test 6: Nested Array")
    print("=" * 60)
    
    class Matrix2x2(Module):
        idx1: INPUT[Logic[1]]
        idx2: INPUT[Logic[1]]
        out: OUTPUT[Logic[8]]
        
        def build(self, io):
            # 2x2 matrix
            inner0 = Array[2, Logic[8]]([Logic[8](0), Logic[8](1)])
            inner1 = Array[2, Logic[8]]([Logic[8](2), Logic[8](3)])
            
            outer = Array[2, Array[2, Logic[8]]]([inner0, inner1])
            
            # Double indexing
            io.out = outer[io.idx1][io.idx2]
    
    mod = Matrix2x2()
    mod.compile()
    print(mod.verilog())
    print("✓ Nested Array test passed\n")


# ============================================================================
# Test 7: Parameterized Struct
# ============================================================================

def test_parameterized_struct():
    print("=" * 60)
    print("Test 7: Parameterized Struct with __add__")
    print("=" * 60)
    
    class Point[WIDTH: int](Struct):
        x: Logic[WIDTH]
        y: Logic[WIDTH]
        
        def __add__(self, other):
            return self.__class__(
                x=self.x + other.x,
                y=self.y + other.y
            )
    
    class PointAdder[WIDTH: int](Module):
        a: INPUT[Point[WIDTH]]
        b: INPUT[Point[WIDTH]]
        out: OUTPUT[Point[WIDTH]]
        
        def build(self, io):
            io.out = io.a + io.b  # Uses Point.__add__
    
    adder = PointAdder[32]()
    adder.compile()
    print(adder.verilog())
    print("✓ Parameterized Struct test passed\n")


# ============================================================================
# Test 8: Mux with different types
# ============================================================================

def test_mux():
    print("=" * 60)
    print("Test 8: Mux")
    print("=" * 60)
    
    class Point(Struct):
        x: Logic[16]
        y: Logic[16]
    
    class MuxTest(Module):
        sel: INPUT[Logic[1]]
        a: INPUT[Point]
        b: INPUT[Point]
        out: OUTPUT[Point]
        
        def build(self, io):
            io.out = Mux[Point](io.sel, io.a, io.b)
    
    mod = MuxTest()
    mod.compile()
    print(mod.verilog())
    print("✓ Mux test passed\n")


# ============================================================================
# Test 9: Struct with Array field
# ============================================================================

def test_struct_with_array():
    print("=" * 60)
    print("Test 9: Struct with Array field")
    print("=" * 60)
    
    class Vector4(Struct):
        data: Array[4, Logic[32]]
        length: Logic[32]
    
    class VectorTest(Module):
        v: INPUT[Vector4]
        idx: INPUT[Logic[2]]
        out: OUTPUT[Logic[32]]
        
        def build(self, io):
            io.out = io.v.data[io.idx]
    
    mod = VectorTest()
    mod.compile()
    print(mod.verilog())
    print("✓ Struct with Array field test passed\n")


# ============================================================================
# Test 10: Deeply nested composability
# ============================================================================

def test_deep_composability():
    print("=" * 60)
    print("Test 10: Deep Composability - Array[N, Array[M, Struct]]")
    print("=" * 60)
    
    class Point(Struct):
        x: Logic[8]
        y: Logic[8]
    
    class DeepTest(Module):
        data: INPUT[Array[2, Array[2, Point]]]
        i: INPUT[Logic[1]]
        j: INPUT[Logic[1]]
        out: OUTPUT[Point]
        
        def build(self, io):
            io.out = io.data[io.i][io.j]
    
    mod = DeepTest()
    mod.compile()
    print(mod.verilog())
    print("✓ Deep Composability test passed\n")


# ============================================================================
# Test 11: Input with Clock
# ============================================================================

def test_input_with_clock():
    print("=" * 60)
    print("Test 11: Input with Clock")
    print("=" * 60)
    
    class ClockDivider(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Clock]
        
        def build(self, io):
            io.out = io.clk
    
    mod = ClockDivider()
    mod.compile()
    print(mod.verilog())
    print("✓ Input with Clock test passed\n")



# ============================================================================
# Test 12: Reg Counter
# ============================================================================

def test_reg_counter():
    print("=" * 60)
    print("Test 12: Reg Counter")
    print("=" * 60)
    
    class Counter(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Logic[32]]
        
        def build(self, io):
            counter = Reg[Logic[32]]()
            
            with io.clk.posedge:
                counter.next = counter + 1
            
            io.out = counter
    
    mod = Counter()
    mod.compile()
    print(mod.verilog())
    print("✓ Reg Counter test passed\n")


# ============================================================================
# Test 13: Reg with Reset
# ============================================================================

def test_reg_with_reset():
    print("=" * 60)
    print("Test 13: Reg with Reset")
    print("=" * 60)
    
    class CounterWithReset(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        out: OUTPUT[Logic[32]]
        
        def build(self, io):
            counter = Reg[Logic[32]]()
            
            # Use both clock and reset context
            with io.clk.posedge as clk, io.rst.negedge as rst:
                counter.next = counter + 1
            
            io.out = counter
    
    mod = CounterWithReset()
    mod.compile()
    print(mod.verilog())
    print("✓ Reg with Reset test passed\n")


# ============================================================================
# Run all tests
# ============================================================================

if __name__ == "__main__":
    test_logic()
    test_parameterized()
    test_struct()
    test_array()
    test_array_of_struct()
    test_nested_array()
    test_parameterized_struct()
    test_mux()
    test_struct_with_array()
    test_deep_composability()
    test_input_with_clock()
    test_reg_counter()
    test_reg_with_reset()
    
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

