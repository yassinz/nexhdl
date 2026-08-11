from nexhdl import *
from random import randrange



def test_array():
    class TestArray(Module):
        a: INPUT[Logic[3]]
        out: OUTPUT[Logic[8]]

        def build(self, io):
            x = Array[8, 8]([1,2,3,4,5,6,7,8])
            io.out = x[io.a]

    module = TestArray()

    with module.simulate() as sim:
        io = sim.io
        for i in range(8):
            io.a = i
            sim.step()
            print(io.out)
            assert io.out == i + 1
    


def test_array_input():
    class TestArrayInput[SIZE: int, WIDTH: int](Module):
        a: INPUT[Array[SIZE, Logic[WIDTH]]]
        b: INPUT[Array[SIZE, Logic[WIDTH]]]

        out: OUTPUT[Array[SIZE, Logic[WIDTH]]]

        def build(self, io):
            result = Array[SIZE, Logic[WIDTH]](
                [io.a[i] + io.b[i] for i in range(SIZE)]
            )
            io.out = result

    module = TestArrayInput[16, 8]()

    with module.simulate() as sim:
        io = sim.io
        for i in range(8):
            io.a = [i] * 16
            io.b = [i * 2] * 16
            sim.step()
            print(io.out)
            assert io.out == [i + i * 2] * 16

    

def test_array_indexing():
    class Point(Struct):
        x: Logic[32]
        y: Logic[32]

    class TestArrayIndexing(Module):
        a:      INPUT[Logic[3]]
        out:    OUTPUT[Logic[16]]

        def build(self, io):
            x = Array[8, 16]([i * 10 for i in range(8)])
            io.out = x[io.a]  

    module = TestArrayIndexing()
    module.compile()
    
    with module.simulate() as sim:
        io = sim.io
        for i in range(8):
            io.a = i
            sim.step()
            expected = i * 10
            print(f"Index {i}: got {io.out}, expected {expected}")
            assert io.out == expected



def test_nested_array():
    class TestNestedArrayIndexing(Module):
        idx1:    INPUT[Logic[2]]
        idx2:    INPUT[Logic[2]]
        out:     OUTPUT[Logic[16]]

        def build(self, io):
            # Create a nested array: Array of 4 Arrays, each containing 4 Logic[8] values
            inner_arrays = []
            for i in range(4):
                inner = Array[4, Logic[16]]([Logic[16](i * 10 + j) for j in range(4)])
                inner_arrays.append(inner)

            outer = Array[4, Array[4, Logic[16]]](inner_arrays)
            # First index should return Array[4, Logic[8]]
            middle = outer[io.idx1]
            # Second index should return Logic[8]
            result = middle[io.idx2]
            io.out = result


    module = TestNestedArrayIndexing()
    module.compile()
    print(module.verilog())
    
    with module.simulate() as sim:
        io = sim.io
        for i in range(4):
            for j in range(4):
                io.idx1 = i
                io.idx2 = j
                sim.step()
                expected = i * 10 + j
                print(f"Index [{i}][{j}]: got {io.out}, expected {expected}")
                assert io.out == expected
    


def test_array_alu():
    class ArrayALU[SIZE: int, WIDTH: int](Module):
        a: INPUT[Array[SIZE, WIDTH]]
        b: INPUT[Array[SIZE, WIDTH]]
        op: INPUT[Logic[2]]
        
        out: OUTPUT[Array[SIZE, WIDTH]]

        def build(self, io):
            result = Array[4, Array[SIZE, WIDTH]]([
                Array[SIZE, WIDTH]([(io.a[i] + io.b[i]) for i in range(SIZE)]),
                Array[SIZE, WIDTH]([(io.a[i] * io.b[i]) for i in range(SIZE)]),
                Array[SIZE, WIDTH]([(io.a[i] - io.b[i]) for i in range(SIZE)]),
                Array[SIZE, WIDTH]([(io.a[i] / io.b[i]) for i in range(SIZE)]),
            ])

            io.out = result[io.op]
    
    SIZE, WIDTH = 4, 16  # Use smaller size for cleaner output
    array_alu = ArrayALU[SIZE, WIDTH]()
    array_alu.compile()

    with array_alu.simulate() as sim:
        io = sim.io
        
        # Create array inputs
        a_vals = [10, 20, 30, 40]
        b_vals = [2, 3, 4, 5]
        
        for op in range(4):
            io.a = a_vals
            io.b = b_vals
            io.op = op
            sim.step()
            
            op_names = ['add', 'mul', 'sub', 'div']
            print(f"op={op_names[op]}: a={a_vals} b={b_vals} -> out={io.out}")



if __name__ == "__main__":

    test_array()
    test_array_input()
    test_array_indexing()
    test_nested_array()
    test_array_alu()