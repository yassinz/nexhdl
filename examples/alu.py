from nexhdl import Module, INPUT, OUTPUT, Logic, Mux, Map, Struct

class ALUOp():
    ADD = 0
    SUB = 1
    AND = 2
    OR  = 3
    XOR = 4
    SHL = 5
    SHR = 6

class ConfigurableALU[WIDTH: int](Module):
    """
    A configurable ALU supporting multiple operations.
    Demonstrates the use of 'Map' for operation decoding.
    """
    a:   INPUT[Logic[WIDTH]]
    b:   INPUT[Logic[WIDTH]]
    op:  INPUT[Logic[3]]
    res: OUTPUT[Logic[WIDTH]]
    zero: OUTPUT[Logic[1]]

    def build(self, io):
        # We can use a Map to select the result based on the opcode
        # This is often cleaner than nested Muxes for many operations
        result = Map[3, Logic[WIDTH]](
            (ALUOp.ADD, io.a + io.b),
            (ALUOp.SUB, io.a - io.b),
            (ALUOp.AND, io.a & io.b),
            (ALUOp.OR,  io.a | io.b),
            (ALUOp.XOR, io.a ^ io.b),
            (ALUOp.SHL, io.a << io.b[0:4].zext(WIDTH)), # Simple shift example
            (ALUOp.SHR, io.a >> io.b[0:4].zext(WIDTH)),
            default=Logic[WIDTH](0)
        )[io.op]

        io.res = result
        io.zero = (result == 0)





if __name__ == "__main__":
    alu = ConfigurableALU[32]()
    print(alu.verilog())
    
    with alu.simulate() as sim:
        # Test Addition
        sim.io.a = 10
        sim.io.b = 20
        sim.io.op = ALUOp.ADD
        sim.step()
        print(f"10 + 20 = {sim.io.res} (zero: {sim.io.zero})")
        assert sim.io.res == 30

        # Test Subtraction
        sim.io.a = 50
        sim.io.b = 50
        sim.io.op = ALUOp.SUB
        sim.step()
        print(f"50 - 50 = {sim.io.res} (zero: {sim.io.zero})")
        assert sim.io.res == 0
        assert sim.io.zero == 1

        # Test XOR
        sim.io.a = 0xAA
        sim.io.b = 0x55
        sim.io.op = ALUOp.XOR
        sim.step()
        print(f"0xAA ^ 0x55 = {hex(sim.io.res)}")
        assert sim.io.res == 0xFF
