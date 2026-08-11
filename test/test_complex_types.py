from nexhdl import *


class Point[WIDTH: int](Struct):
    x: Logic[WIDTH]
    y: Logic[WIDTH]
    
    def __add__(self, other):
        return self.__class__(x=self.x + other.x, y=self.y + other.y)


class Vector[N: int, WIDTH: int](Struct):
    data: Array[N, Point[WIDTH]]

    def __add__(self, other):
        Points = [self.data[i] + other.data[i] for i in range(N)]
        return self.__class__(data=Array[N, Point[WIDTH]](Points))


class AdderPoint[WIDTH: int](Module):
    a: INPUT[Point[WIDTH]]
    b: INPUT[Point[WIDTH]]
    out: OUTPUT[Point[WIDTH]]
    
    def build(self, io):
        io.out = io.a + io.b  # Uses Point.__add__


class AdderVector[WIDTH: int](Module):
    a: INPUT[Vector[8, WIDTH]]
    b: INPUT[Vector[8, WIDTH]]
    out: OUTPUT[Vector[8, WIDTH]]
    
    def build(self, io):
        io.out = io.a + io.b  # Uses Vector.__add__



def test_complex_types():
    print("=== Testing AdderPoint[32] Simulation ===")
    alu = AdderPoint[32]()
    alu.compile()
    # print(alu.verilog())
    
    with alu.simulate() as sim:
        sim.io.a = {'x': 10, 'y': 20}
        sim.io.b = {'x': 5, 'y': 15}
        sim.step()
        print(f"ALU Output: {sim.io.out}")
        assert sim.io.out == {'x': 15, 'y': 35}

    print("\n=== Testing AdderVector[32] Simulation ===")
    vec_alu = AdderVector[32]()
    vec_alu.compile()
    
    with vec_alu.simulate() as sim:
        # Array[8, Point[32]]
        a_data = [{'x': i, 'y': i*2} for i in range(8)]
        b_data = [{'x': 100, 'y': 200} for _ in range(8)]
        
        sim.io.a = {'data': a_data}
        sim.io.b = {'data': b_data}
        sim.step()
        
        output = sim.io.out
        print(f"Vector ALU Result (first 2 elems): {output['data'][:2]}")
        assert output['data'][0] == {'x': 100, 'y': 200}
        assert output['data'][1] == {'x': 101, 'y': 202}

    print("\n✓ Complex types simulation passed!")


if __name__ == "__main__":
    test_complex_types()

