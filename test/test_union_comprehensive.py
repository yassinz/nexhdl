from nexhdl import *
from circt.ir import Module, InsertionPoint

def test_union_comprehensive():
    m = Module.parse('module {}')
    with InsertionPoint(m.body):
        print("\n" + "="*60)
        print("Union Field Type Test - Comprehensive")
        print("="*60 + "\n")
    
        # Test 1: Simple types
        class SimpleUnion(Union):
            u8: Logic[8]
            u16: Logic[16]
            u32: Logic[32]
    
        u = SimpleUnion(u32=Logic[32](0x12345678))
        assert isinstance(u.u8, Logic) and u.u8.width == 8
        assert isinstance(u.u16, Logic) and u.u16.width == 16
        assert isinstance(u.u32, Logic) and u.u32.width == 32
        print("✓ Test 1: Simple Logic types return correct widths")
    
        # Test 2: Struct fields
        class Point(Struct):
            x: Logic[16]
            y: Logic[16]
    
        class StructUnion(Union):
            logic: Logic[32]
            point: Point
    
        u2 = StructUnion(logic=Logic[32](0xAABBCCDD))
        point_result = u2.point
        assert hasattr(point_result, 'x') and hasattr(point_result, 'y')
        assert isinstance(point_result.x, Logic) and point_result.x.width == 16
        print("✓ Test 2: Struct fields return proper Struct type with accessible fields")
    
        # Test 3: Array fields
        class ArrayUnion(Union):
            logic: Logic[64]
            arr: Array[4, Logic[16]]
    
        u3 = ArrayUnion(logic=Logic[64](0x1111222233334444))
        arr_result = u3.arr
        assert hasattr(arr_result, '__getitem__')
        elem = arr_result[0]
        assert isinstance(elem, Logic) and elem.width == 16
        print("✓ Test 3: Array fields return proper Array type with indexing")
    
        # Test 4: Nested struct with array
        class Vector(Struct):
            data: Array[2, Logic[16]]
    
        class NestedUnion(Union):
            logic: Logic[32]
            vec: Vector
    
        u4 = NestedUnion(logic=Logic[32](0x12345678))
        vec_result = u4.vec
        assert hasattr(vec_result, 'data')
        assert hasattr(vec_result.data, '__getitem__')
        print("✓ Test 4: Nested Struct with Array field works correctly")
    
        print("\n" + "="*60)
        print("All Union field type tests passed!")
        print("="*60 + "\n")

if __name__ == "__main__":
    test_union_comprehensive()
