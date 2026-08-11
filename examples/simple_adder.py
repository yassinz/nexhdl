from nexhdl import *



def simple_adder():
    class SimpleAdder[WIDTH: int](Module):
        """A basic combinational adder."""
        a:   INPUT[Logic[WIDTH]]
        b:   INPUT[Logic[WIDTH]]
        res: OUTPUT[Logic[WIDTH]]

        def build(self, io):
            # Combinational logic is simple arithmetic
            io.res = io.a + io.b

    # Compile and print Verilog
    dut = SimpleAdder[17]()
    print("--- Verilog ---")
    print(dut.verilog())

    # Quick simulation
    with dut.simulate() as sim:
        sim.io.a = 15
        sim.io.b = 27
        sim.step()
        print(f"Simulation: {sim.io.a} + {sim.io.b} = {sim.io.res}")
        assert sim.io.res == 42



def array_adder():
    class ArrayAdder[SIZE: int, WIDTH: int](Module):
        """A basic combinational adder."""
        a:   INPUT[Array[SIZE, Logic[WIDTH]]]
        b:   INPUT[Array[SIZE, Logic[WIDTH]]]
        res: OUTPUT[Array[SIZE, Logic[WIDTH]]]

        def build(self, io):
            io.res = Array[SIZE, Logic[WIDTH]](
                [io.a[i] + io.b[i] for i in range(SIZE)]
            )

    # Compile and print Verilog
    dut = ArrayAdder[4, 8]()
    print("--- Verilog ---")
    print(dut.verilog())

    # Quick simulation
    with dut.simulate() as sim:
        sim.io.a = [1, 2, 3, 4]
        sim.io.b = [5, 6, 7, 8]
        sim.step()
        print(f"Simulation: {sim.io.a} + {sim.io.b} = {sim.io.res}")
        assert sim.io.res == [6, 8, 10, 12]
    


def struct_adder():
    class Point[WIDTH: int](Struct):
        x: Logic[WIDTH]
        y: Logic[WIDTH]

        def __add__(self, other):
            return Point[WIDTH](
                x=self.x + other.x,
                y=self.y + other.y
            )

    class PointAdder[WIDTH: int](Module):
        """A basic combinational adder."""
        a:   INPUT[Point[WIDTH]]
        b:   INPUT[Point[WIDTH]]
        res: OUTPUT[Point[WIDTH]]

        def build(self, io):
            io.res = io.a + io.b  # Use the __add__ method

    # Compile and print Verilog
    dut = PointAdder[8]()
    print("--- Verilog ---")
    print(dut.verilog())

    # Quick simulation
    with dut.simulate() as sim:
        sim.io.a = {'x': 1, 'y': 2}
        sim.io.b = {'x': 3, 'y': 4}
        sim.step()
        print(f"Simulation: {sim.io.a} + {sim.io.b} = {sim.io.res}")
        assert sim.io.res == {'x': 4, 'y': 6}


def big_adder():
    class BigAdder(Module):
        """A basic combinational adder."""
        a:   INPUT[Logic[512]]
        b:   INPUT[Logic[512]]
        res: OUTPUT[Logic[512]]

        def build(self, io):
            io.res = io.a + io.b

    # Compile and print Verilog
    dut = BigAdder()
    print("--- Verilog ---")
    print(dut.verilog())

    # Quick simulation
    with dut.simulate() as sim:
        sim.io.a = 0x12345678_90123456_78901234_56789012_12345678_90123456_78901234_56789012
        sim.io.b = 0x12345678_90123456_78901234_56789012_12345678_90123456_78901234_56789012
        sim.step()
        print(f"Simulation: {sim.io.a} + {sim.io.b} = {sim.io.res}")
        assert sim.io.res == sim.io.a + sim.io.b




if __name__ == "__main__":
    simple_adder()
    array_adder()
    struct_adder()
    big_adder()

