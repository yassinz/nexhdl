from nexhdl import *



def test_param_adder():
    class ParamAdder[WIDTH: int](Module):
        a:  INPUT[Logic[WIDTH]]
        b:  INPUT[Logic[WIDTH]]

        out: OUTPUT[Logic[WIDTH * 2]]
        
        def build(self, io):
            # WIDTH is a TypeVar in this scope, so we must use io.WIDTH to get the value
            # Extend inputs to match output width (WIDTH * 2)
            io.out = io.a.zext(WIDTH * 2) * io.b.zext(WIDTH * 2)

    param_adder = ParamAdder[32]()
    print("Successfully created ParamAdder instance")

    with param_adder.simulate() as sim:
        io = sim.io
        io.a = 42
        io.b = 100
        sim.step()
        assert io.out == 42 * 100    



class ParamType[DTYPE: type](Module):
    a: INPUT[DTYPE]
    b: INPUT[DTYPE]
    sel: INPUT[Logic[1]]
    out: OUTPUT[DTYPE]
    
    def build(self, io):
        io.out = Mux[DTYPE](io.sel, io.a, io.b)

def test_param_type():
    # Test with an array
    param_type = ParamType[Array[8, Logic[32]]]()

    with param_type.simulate() as sim:
        io = sim.io
        io.a = [1, 2, 3, 4, 5, 6, 7, 8]
        io.b = [8, 7, 6, 5, 4, 3, 2, 1]
        io.sel = 1
        sim.step()
        assert io.out == io.a
        io.sel = 0
        sim.step()
        assert io.out == io.b

    # Test with a logic
    param_type = ParamType[Logic[32]]()

    with param_type.simulate() as sim:
        io = sim.io
        io.a = 42
        io.b = 100
        io.sel = 0
        sim.step()
        assert io.out == 100
        io.sel = 1
        sim.step()
        assert io.out == 42
    
    # Test with a struct
    class Point(Struct):
        x: Logic[32]
        y: Logic[32]

    param_type = ParamType[Point]()

    with param_type.simulate() as sim:
        io = sim.io
        io.a = {"x": 1, "y": 2}
        io.b = {"x": 3, "y": 4}
        io.sel = 0
        sim.step()
        assert io.out == {"x": 3, "y": 4}
        io.sel = 1
        sim.step()
        assert io.out == {"x": 1, "y": 2}





if __name__ == "__main__":
    test_param_adder()
    test_param_type()
