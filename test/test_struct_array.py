from nexhdl import *





class PointParam[WIDTH](Struct):
    x: Logic[WIDTH]
    y: Logic[WIDTH]

    def __add__(self, other):
        return self.__class__(x=(self.x + other.x), y=(self.y + other.y))

    def __sub__(self, other):
        return self.__class__(x=(self.x - other.x), y=(self.y - other.y))
    
    def __or__(self, other):
        return self.__class__(x=(self.x | other.x), y=(self.y | other.y))
    
    def __and__(self, other):
        return self.__class__(x=(self.x & other.x), y=(self.y & other.y))
    

class Vector[SIZE, WIDTH](Struct):
    data: Array[SIZE, Logic[WIDTH]]

    def __add__(self, other):
        data = Array[SIZE, Logic[WIDTH]]([self.data[i] + other.data[i] for i in range(SIZE)])
        return self.__class__(data=data)

    def __sub__(self, other):
        data = Array[SIZE, Logic[WIDTH]]([self.data[i] - other.data[i] for i in range(SIZE)])
        return self.__class__(data=data)
    
    def __or__(self, other):
        data = Array[SIZE, Logic[WIDTH]]([self.data[i] | other.data[i] for i in range(SIZE)])
        return self.__class__(data=data)
    
    def __and__(self, other):
        data = Array[SIZE, Logic[WIDTH]]([self.data[i] & other.data[i] for i in range(SIZE)])
        return self.__class__(data=data)




class TestStructParam[DATATYPE: type](Module):
    a:      INPUT[DATATYPE]
    b:      INPUT[DATATYPE]
    sel:    INPUT[Logic[2]]

    out:    OUTPUT[DATATYPE]

    def build(self, io):
        ops = [
            io.a + io.b, 
            io.a - io.b, 
            io.a | io.b, 
            io.a & io.b
        ]

        io.out = Array[4, DATATYPE](ops)[io.sel]
        



def test_struct_param():
    module = TestStructParam[PointParam[32]]()
    module.compile()

    results = [
        {'x': 6, 'y': 12},
        {'x': 4, 'y': 2},
        {'x': 5, 'y': 7},
        {'x': 1, 'y': 5},
    ]

    with module.simulate() as sim:
        for i in range(4):
            io = sim.io
            io.a = {'x': 5, 'y': 7}
            io.b = {'x': 1, 'y': 5}
            io.sel = i
            sim.step()
            print(f"Index {i}: {io.out}")
            assert io.out == results[i]



    module = TestStructParam[Vector[4, 8]]()
    module.compile()

    results = [
        {'data': [6, 6, 4, 6]},
        {'data': [4, 252, 0, 0]},
        {'data': [5, 5, 2, 3]},
        {'data': [1, 1, 2, 3]}
    ]
    
    with module.simulate() as sim:
        for i in range(4):
            io = sim.io
            io.a = {"data": [5, 1, 2, 3]}
            io.b = {"data": [1, 5, 2, 3]}
            io.sel = i
            sim.step()
            print(f"Index {i}: {io.out}")
            assert io.out == results[i]



class Point(Struct):
    x: Logic[8]
    y: Logic[8]


class TestStructArray(Module):
    idx: INPUT[Logic[2]]
    out_x: OUTPUT[Logic[8]]
    out_y: OUTPUT[Logic[8]]

    def build(self, io):
        points = []
        for i in range(4):
            p = Point(x=(i * 10), y=(i * 20))
            points.append(p)
        
        arr = Array[4, Point](points)

        result = arr[io.idx]
        
        io.out_x = result.x
        io.out_y = result.y


def test_struct_array():
    module = TestStructArray()
    module.compile()


    with Simulator(module.module, module.name) as sim:
        io = sim.io
        for i in range(4):
            io.idx = i
            sim.step()
            print(f"Index {i}: x={io.out_x}, y={io.out_y}")
            assert io.out_x == i * 10
            assert io.out_y == i * 20
    
    

class Status[W](Struct):
    count: Logic[W]
    active: Logic[1]

class StructWithOddWidth[W: int](Module):
    count:  INPUT[Logic[W]]
    active: INPUT[Logic[1]]
    out:   OUTPUT[Status[W]]
    c_out: OUTPUT[Logic[W]]
    a_out: OUTPUT[Logic[1]]

    def build(self, io):
        s = Status[W](count=io.count, active=io.active)
        io.out = s
        io.c_out = s.count
        io.a_out = s.active


def test_struct_with_odd_width():
    # 1. Instantiate the Design Under Test (DUT)
    dut = StructWithOddWidth[13]()

    # 2. Start simulation
    with dut.simulate() as sim:
        # Set input struct values
        sim.io.count = 41
        sim.io.active = 1
        sim.step()
        
        # Verify output struct values
        print(f"Output state: {sim.io.out}, c_out: {sim.io.c_out}, a_out: {sim.io.a_out}")
        assert sim.io.out['count'] == 41
        assert sim.io.out['active'] == 1
        
        print("\nSimulation Passed: StructWithOddWidth struct handling is correct.")



class ArrayWithOddWidth[W: int](Module):
    a: INPUT[Logic[W]]
    b: INPUT[Logic[W]]
    c: INPUT[Logic[W]]
    d: INPUT[Logic[W]]

    out: OUTPUT[Array[4, Logic[W]]]

    def build(self, io):
        io.out = Array[4, Logic[W]]([io.a, io.b, io.c, io.d])


def test_array_with_odd_width():
    # 1. Instantiate the Design Under Test (DUT)
    dut = ArrayWithOddWidth[17]()

    # 2. Start simulation
    with dut.simulate() as sim:
        # Set individual inputs
        sim.io.a = 10
        sim.io.b = 20
        sim.io.c = 30
        sim.io.d = 40
        sim.step()
        
        # Verify output array values
        print(f"Output array: {sim.io.out}")
        assert sim.io.out == [10, 20, 30, 40]
        
        print("\nSimulation Passed: ArrayWithOddWidth array handling is correct.")



def test_counter():
    class Point(Struct):
        x: Logic[32]
        y: Logic[32]

    class Counter(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Logic[32]]
        point_out: OUTPUT[Point]

        def build(self, io):
            # Initialize registers
            counter = Reg[32]()
            point_reg = Reg[Point]()

            with io.clk.posedge:
                # Update the counter and point register
                counter.next = counter + 1
                point_reg.next = Point(x=point_reg.x + 3, y=point_reg.y + 2)

            io.out = counter
            io.point_out = point_reg

    dut = Counter()
    dut.compile()

    with dut.simulate() as sim:
        io = sim.io
        for i in range(10):
            sim.tick()
            # Verify the counter and point values
            print(f"Count: {io.out} Point: {io.point_out}")
            assert io.out == i + 1
            assert io.point_out['x'] == (i+1) * 3
            assert io.point_out['y'] == (i+1) * 2





if __name__ == "__main__":
    test_struct_array()
    test_struct_param()
    test_struct_with_odd_width()
    test_array_with_odd_width()
    test_counter()