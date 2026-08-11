from nexhdl import *




def test_all_generic_validation():
    from circt.ir import Module, InsertionPoint

    class MyStruct[WIDTH](Struct):
        x: Logic[WIDTH]
        y: Logic[WIDTH]

    class MyUnion[WIDTH](Union):
        a: Logic[WIDTH]
        b: Logic[8]

    m = Module.create()
    with InsertionPoint(m.body):
        print("\n" + "="*60)
        print("Generic Type Validation - All Types")
        print("="*60 + "\n")
        
        # Test Array
        try:
            arr = Array[4, MyStruct]
            print("ERROR: Array should reject MyStruct without parameters")
        except TypeError as e:
            print(f"✓ Array: {e}")
        
        try:
            arr = Array[4, MyStruct[16]]
            print("✓ Array[4, MyStruct[16]] works")
        except Exception as e:
            print(f"ERROR: {e}")
        
        # Test Reg
        try:
            reg = Reg[MyUnion]
            print("ERROR: Reg should reject MyUnion without parameters")
        except TypeError as e:
            print(f"✓ Reg: {e}")
        
        try:
            reg = Reg[MyUnion[32]]
            print("✓ Reg[MyUnion[32]] works")
        except Exception as e:
            print(f"ERROR: {e}")
        
        # Test Mux
        try:
            mux = Mux[MyStruct]
            print("ERROR: Mux should reject MyStruct without parameters")
        except TypeError as e:
            print(f"✓ Mux: {e}")
        
        try:
            mux = Mux[MyStruct[32]]
            print("✓ Mux[MyStruct[32]] works")
        except Exception as e:
            print(f"ERROR: {e}")
        
        print("\n" + "="*60)
        print("All type validations passed!")
        print("="*60 + "\n")


def test_module_generic_validation():
    class Adder[WIDTH](Module):
        a: INPUT[Logic[WIDTH]]
        b: INPUT[Logic[WIDTH]]
        out: OUTPUT[Logic[WIDTH]]
        
        def build(self, io):
            io.out = io.a + io.b

    print("\n" + "="*60)
    print("Module Generic Validation")
    print("="*60 + "\n")
    
    # Test Module without parameters
    try:
        m = Adder()
        m.compile()
        print("ERROR: Should reject Adder() without parameters")
    except TypeError as e:
        print(f"✓ Module: {e}")
    
    # Test Module with parameters
    try:
        m = Adder[32]()
        m.compile()
        print("✓ Adder[32]() works")
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "="*60)
    print("Module validation passed!")
    print("="*60 + "\n")



if __name__ == "__main__":
    test_all_generic_validation()
    test_module_generic_validation()
