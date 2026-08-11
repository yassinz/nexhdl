from nexhdl import Module, INPUT, OUTPUT, Logic, Array, Param

# Define a validator for power-of-two sizes
PowerOf2 = Param[int](lambda x: x > 0 and (x & (x - 1)) == 0, "Must be power of 2")

class VectorProcessor[SIZE: PowerOf2, WIDTH: int](Module):
    """
    A parameterized processor that adds two vectors of fixed size.
    Uses 'Param' to ensure SIZE is always a power of 2.
    """
    vec_a: INPUT[Array[SIZE, Logic[WIDTH]]]
    vec_b: INPUT[Array[SIZE, Logic[WIDTH]]]
    vec_res: OUTPUT[Array[SIZE, Logic[WIDTH]]]

    def build(self, io):
        # Build the result array by adding components
        # Note: In nexhdl, we can iterate over Arrays to build new ones
        results = [a + b for a, b in zip(io.vec_a, io.vec_b)]
        io.vec_res = Array[SIZE, Logic[WIDTH]](results)

if __name__ == "__main__":
    # This will work
    dut = VectorProcessor[4, 16]()
    print(dut.verilog())
    print(f"Created VectorProcessor with SIZE={dut.SIZE}")

    try:
        # This will fail at specialization time
        bad_dut = VectorProcessor[7, 16]()
    except ValueError as e:
        print(f"Validation caught error: {e}")

    with dut.simulate() as sim:
        sim.io.vec_a = [1, 2, 3, 4]
        sim.io.vec_b = [10, 20, 30, 40]
        sim.step()
        print(f"Result Vector: {sim.io.vec_res}")
        assert sim.io.vec_res == [11, 22, 33, 44]
