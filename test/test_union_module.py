from nexhdl import *



class Point(Struct):
    x: Logic[16]
    y: Logic[16]

class MyUnion(Union):
    logic: Logic[32]
    point: Point

class UnionTest(Module):
    u_in: INPUT[MyUnion]
    sel: INPUT[Logic[1]]
    out: OUTPUT[Logic[16]]
    
    def build(self, io):
        # Access union fields - should return proper types
        logic_val = io.u_in.logic
        point_val = io.u_in.point
        
        # Use the fields
        io.out = Mux[Logic[16]](io.sel, logic_val[0:16], point_val.x)

def test_union_in_module():
    print("\n=== Testing Union in Module ===\n")
    
    mod = UnionTest()
    mod.compile()
    print("✓ Module with union field access compiled")
    print(mod.verilog())
    print("\n✓ Union fields work correctly in modules!\n")



def test_union_simple():
    from circt.ir import Module, InsertionPoint
    m = Module.parse('module {}')
    with InsertionPoint(m.body):
        print("\n=== Testing Simple Union Field Access ===\n")
        
        # Create union with logic field
        u1 = MyUnion(logic=Logic[32](0x12345678))
        print(f"✓ Created union with logic field")
    
        # Access logic field - should return Logic[32]
        result_logic = u1.logic
        print(f"✓ Accessed logic field: {type(result_logic).__name__}")
        assert isinstance(result_logic, Logic), "Should return Logic"
        assert result_logic.width == 32, "Should be 32 bits"
        print(f"✓ logic field has correct type: Logic[32]")
        
        # Access point field - should return Point (Struct)
        result_point = u1.point
        print(f"✓ Accessed point field: {type(result_point).__name__}")
        assert hasattr(result_point, 'x'), "Should have x field"
        assert hasattr(result_point, 'y'), "Should have y field"
        print(f"✓ point field has correct type: Point with x and y")
        
        print("\n✓ Union fields return proper types!\n")



class XUnion(Union):
    a: Logic[32]
    b: Logic[16]

def test_union_error():
    print("\n=== Testing Union Error Messages ===\n")
    
    # Create a Union (32 bits - max of fields)
    u = XUnion(a=Logic[32](0x12345678))
    
    try:
        # Try to cast to wrong size
        wrong = Logic[64](u)
    except ValueError as e:
        print(f"✓ Union error message:\n  {e}\n")
    
    # Correct cast
    correct = Logic[32](u)
    print(f"✓ Correct cast Logic[32](Union) works!\n")



if __name__ == "__main__":
    test_union_in_module()
    test_union_simple()
    test_union_error()
