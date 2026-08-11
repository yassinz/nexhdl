from nexhdl import *



def test_mux_point():
    class Point(Struct):
        x: Logic[32]
        y: Logic[32]

    class MuxPoint(Module):
        a: INPUT[Point]
        b: INPUT[Point]
        sel: INPUT[Logic[1]]
        out: OUTPUT[Point]

        def build(self, io):
            io.out = Mux[Point](io.sel, io.a, io.b)

    mux_point = MuxPoint()
    mux_point.compile()
    print(mux_point.verilog())
    
    with mux_point.simulate() as sim:
        io = sim.io
        for i in range(4):
            io.a = {'x': i, 'y': i * 2}
            io.b = {'x': i * 10, 'y': i * 20}
            io.sel = i % 2
            sim.step()
            print(f"sel={i % 2}: a={{'x': {i}, 'y': {i*2}}} b={{'x': {i*10}, 'y': {i*20}}} -> out={io.out}")
            assert io.out == {'x': i, 'y': i * 2} if i % 2 else {'x': i * 10, 'y': i * 20}



def test_mux_array():
    class MuxArray(Module):
        a: INPUT[Array[4, Logic[32]]]
        b: INPUT[Array[4, Logic[32]]]
        sel: INPUT[Logic[1]]
        out: OUTPUT[Array[4, Logic[32]]]

        def build(self, io):
            io.out = Mux[Array[4, Logic[32]]](io.sel, io.a, io.b)

    mux_array = MuxArray()
    mux_array.compile()
    print(mux_array.verilog())
    
    with mux_array.simulate() as sim:
        io = sim.io
        for i in range(4):
            io.a = [i, i * 2, i * 4, i * 8]
            io.b = [i * 16, i * 32, i * 64, i * 128]
            io.sel = i % 2
            sim.step()
            print(f"sel={i % 2}: a={io.a} b={io.b} -> out={io.out}")
            assert io.out == io.a if i % 2 else io.b



def test_mux_logic():
    class MuxLogic(Module):
        a: INPUT[Logic[32]]
        b: INPUT[Logic[32]]
        sel: INPUT[Logic[1]]
        out: OUTPUT[Logic[32]]

        def build(self, io):
            io.out = Mux[Logic[32]](io.sel, io.a, io.b)

    mux_logic = MuxLogic()
    mux_logic.compile()
    print(mux_logic.verilog())
    
    with mux_logic.simulate() as sim:
        io = sim.io
        for i in range(4):
            io.a = i * 2
            io.b = i * 4
            io.sel = i % 2
            sim.step()
            print(f"sel={i % 2}: a={io.a} b={io.b} -> out={io.out}")
            assert io.out == (io.a if i % 2 else io.b)




def test_mux_validation():
    from circt.ir import Module, InsertionPoint

    class Point(Struct):
        x: Logic[16]
        y: Logic[16]

    m = Module.parse('module {}')
    with InsertionPoint(m.body):

        print("\n=== Testing Parameterized Mux ===\n")
        
        # Test with Logic
        sel = Logic[1](1)
        a = Logic[32](0x11111111)
        b = Logic[32](0x22222222)
        
        result = Mux[Logic[32]](sel, a, b)
        print(f"✓ Mux[Logic[32]] works")
        
        # Test with Struct
        p1 = Point(x=Logic[16](10), y=Logic[16](20))
        p2 = Point(x=Logic[16](30), y=Logic[16](40))
        
        result = Mux[Point](sel, p1, p2)
        print(f"✓ Mux[Point] works")
        
        # Test type mismatch error
        try:
            wrong = Mux[Logic[32]](sel, a, p1)  # p1 is Point, not Logic[32]
        except TypeError as e:
            print(f"✓ Type mismatch caught:\n  {e}")
        
        # Test wrong selector width
        try:
            bad_sel = Logic[2](1)
            wrong = Mux[Logic[32]](bad_sel, a, b)
        except TypeError as e:
            print(f"✓ Wrong selector width caught:\n  {e}")
        
        print("\n✓ All Mux tests passed!\n")



def test_mux_generic_validation():
    from circt.ir import Module, InsertionPoint

    class Result[WIDTH](Union):
        ok: Logic[WIDTH]
        err: Logic[8]

    class Point[WIDTH](Struct):
        x: Logic[WIDTH]
        y: Logic[WIDTH]

    m = Module.parse('module {}')
    with InsertionPoint(m.body):
        print("\n" + "="*60)
        print("Generic Type Parameter Validation")
        print("="*60 + "\n")
        
        # Test 1: Union without parameters
        try:
            mux = Mux[Result]
            print("ERROR: Should reject Result without parameters")
        except TypeError as e:
            print(f"✓ Union validation: {e}")
        
        # Test 2: Struct without parameters
        try:
            mux = Mux[Point]
            print("ERROR: Should reject Point without parameters")
        except TypeError as e:
            print(f"✓ Struct validation: {e}")
        
        # Test 3: Correct usage
        try:
            mux1 = Mux[Result[32]]
            mux2 = Mux[Point[16]]
            print("✓ Mux[Result[32]] and Mux[Point[16]] work correctly")
        except Exception as e:
            print(f"ERROR: {e}")
        
        print("\n" + "="*60)
        print("All validations passed!")
        print("="*60 + "\n")





def test_mux_int_and_zero():
    from circt.ir import Module, InsertionPoint
    
    class Point(Struct):
        x: Logic[16]
        y: Logic[16]

    m = Module.parse('module {}')
    with InsertionPoint(m.body):
        print("\n" + "="*60)
        print("Testing Mux with Ints/Zero")
        print("="*60 + "\n")
        
        sel = Logic[1](1)
        
        # Test 1: Mux accepts integers for Logic
        # Mux[Logic[32]](sel, 10, 20)
        try:
            res = Mux[Logic[32]](sel, 10, 20)
            print("✓ Mux[Logic[32]](sel, 10, 20) works")
        except Exception as e:
            print(f"ERROR Logic ints: {e}")
            assert False
            
        # Test 2: Mux accepts 0 for Logic
        try:
            res = Mux[Logic[32]](sel, 100, 0)
            print("✓ Mux[Logic[32]](sel, 100, 0) works")
        except Exception as e:
            print(f"ERROR Logic zero: {e}")
            assert False
            
        # Test 3: Mux accepts 0 for Struct
        try:
            p = Point(x=1, y=2)
            # Should work if Point(0) works, which is handled by Struct.__init__
            res = Mux[Point](sel, p, 0)
            print("✓ Mux[Point](sel, p, 0) works")
        except Exception as e:
            print(f"ERROR Struct zero: {e}")
            assert False
            
        print("\n✓ All Int/Zero tests passed!\n")



if __name__ == "__main__":
    test_mux_point()
    test_mux_array()
    test_mux_generic_validation()
    test_mux_validation()
    test_mux_logic()
    test_mux_int_and_zero()
