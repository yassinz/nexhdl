import pytest
from nexhdl import Module, INPUT, OUTPUT, Reg, Wire, Logic, Clock

def test_unconnected_reg():
    class BadReg(Module):
        out: OUTPUT[Logic[32]]
        def build(self, io):
            r = Reg[32]() # Created but not assigned
            io.out = r

    m = BadReg()
    with pytest.raises(RuntimeError, match="Reg 'r' inside module 'BadReg' was created but never assigned"):
        m.compile()

def test_connected_reg():
    class GoodReg(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Logic[32]]
        def build(self, io):
            r = Reg[32]()
            with io.clk.posedge:
                r.next = 0
            io.out = r

    m = GoodReg()
    # Should not raise
    m.compile()

def test_unconnected_wire():
    class BadWire(Module):
        out: OUTPUT[Logic[32]]
        def build(self, io):
            w = Wire[32]()
            io.out = w
            # w.assign never called

    m = BadWire()
    with pytest.raises(RuntimeError, match="Wire 'w' inside module 'BadWire' was created but never assigned"):
        m.compile()

def test_connected_wire():
    class GoodWire(Module):
        out: OUTPUT[Logic[32]]
        def build(self, io):
            w = Wire[32]()
            w.assign = 10
            io.out = w

    m = GoodWire()
    # Should not raise
    m.compile()

def test_nested_scoping():
    """Ensure parent checks don't see child regs and vice versa."""
    
    class Child(Module):
        clk: INPUT[Clock]
        inp: INPUT[Logic[32]]
        out: OUTPUT[Logic[32]]
        def build(self, io):
            r = Reg[32]()
            with io.clk.posedge:
                r.next = io.inp
            io.out = r
    
    class Parent(Module):
        clk: INPUT[Clock]
        out: OUTPUT[Logic[32]]
        def build(self, io):
            # Instantiate Child with input to get hardware instance
            c = Child(inp=Logic[32](1), clk=io.clk)
            # Parent creates a reg but doesn't assign it -> should fail
            bad_r = Reg[32]() 
            # bad_r.next IS MISSING
            io.out = c.out + bad_r
    
    m = Parent()
    # Parent should fail, but Child (compiled inside) should have passed its own checks.
    # Since Parent fails during build, compile raises.
    with pytest.raises(RuntimeError, match="Reg 'bad_r' inside module 'Parent'"):
        m.compile()


if __name__ == "__main__":
    test_unconnected_reg()
    test_connected_reg()
    test_unconnected_wire()
    test_connected_wire()
    test_nested_scoping()
    print("All tests passed!")