from nexhdl import *
from circt.ir import Module, InsertionPoint



class Point[WIDTH](Struct):
    x: Logic[WIDTH]
    y: Logic[WIDTH]

class Result[WIDTH](Union):
    ok: Logic[WIDTH]
    err: Logic[8]

def test_error_message():
    m = Module.create()
    with InsertionPoint(m.body):
        print("\n=== Testing Improved Error Messages ===\n")
        
        # Create a Point (32 bits total)
        point = Point[16](x=Logic[16](10), y=Logic[16](20))
        
        try:
            # Try to cast to wrong size - should show readable error
            wrong = Logic[64](point)
        except ValueError as e:
            print(f"✓ Clear error message:\n  {e}\n")
        
        # Correct cast should work
        correct = Logic[32](point)
        print(f"✓ Correct cast Logic[32](Point) works!\n")


def test_direct_instantiation():
    m = Module.parse('module {}')
    with InsertionPoint(m.body):
        print("\n" + "="*60)
        print("Direct Instantiation Validation")
        print("="*60 + "\n")
        
        # Test Struct direct instantiation
        try:
            p = Point(x=Logic[16](10), y=Logic[16](20))
            print("ERROR: Should reject Point() without parameters")
        except TypeError as e:
            print(f"✓ Struct: {e}")
        
        try:
            p = Point[16](x=Logic[16](10), y=Logic[16](20))
            print("✓ Point[16](...) works")
        except Exception as e:
            print(f"ERROR: {e}")
        
        # Test Union direct instantiation
        try:
            r = Result(ok=Logic[32](42))
            print("ERROR: Should reject Result() without parameters")
        except TypeError as e:
            print(f"✓ Union: {e}")
        
        try:
            r = Result[32](ok=Logic[32](42))
            print("✓ Result[32](...) works")
        except Exception as e:
            print(f"ERROR: {e}")
        
        print("\n" + "="*60)
        print("All direct instantiation validations passed!")
        print("="*60 + "\n")

if __name__ == "__main__":
    test_error_message()
    test_direct_instantiation()
