from nexhdl import *

# 1. Basic Struct with various field types (Byte aligned)
class SubStruct(Struct):
    f1: Logic[8]
    f2: Logic[8]

class MainStruct(Struct):
    a: Logic[16]
    b: SubStruct
    c: Array[2, Logic[8]]

class StructProbe(Module):
    s_in: INPUT[MainStruct]
    
    a_out:  OUTPUT[Logic[16]]
    f1_out: OUTPUT[Logic[8]]
    f2_out: OUTPUT[Logic[8]]
    c0_out: OUTPUT[Logic[8]]
    c1_out: OUTPUT[Logic[8]]
    
    raw_out: OUTPUT[Logic[48]] # 16 + 16 + 16 = 48 bits

    def build(self, io):
        # Extract fields
        io.a_out = io.s_in.a
        io.f1_out = io.s_in.b.f1
        io.f2_out = io.s_in.b.f2
        io.c0_out = io.s_in.c[0]
        io.c1_out = io.s_in.c[1]
        
        # Bitcast to raw bits
        io.raw_out = Logic[48](io.s_in)

def test_struct_serialization():
    dut = StructProbe()
    dut.compile()
    
    with dut.simulate() as sim:
        # Input data
        test_val = {
            "a": 0xAAAA,
            "b": {"f1": 0x11, "f2": 0x22},
            "c": [0x33, 0x44]
        }
        
        sim.io.s_in = test_val
        sim.step()
        
        # Check individual port extractions
        assert sim.io.a_out == 0xAAAA
        assert sim.io.f1_out == 0x11
        assert sim.io.f2_out == 0x22
        assert sim.io.c0_out == 0x33
        assert sim.io.c1_out == 0x44

        print(hex(sim.io.raw_out))
        # Expected: 0xAAAA11223344
        assert sim.io.raw_out == 0xAAAA11223344

# 2. Struct with Methods
class Vector2D(Struct):
    x: Logic[16]
    y: Logic[16]
    
    def sum(self):
        return self.x + self.y

class VectorTest(Module):
    v: INPUT[Vector2D]
    s: OUTPUT[Logic[16]]
    def build(self, io):
        io.s = io.v.sum()

def test_struct_methods():
    dut = VectorTest()
    dut.compile()
    with dut.simulate() as sim:
        sim.io.v = {"x": 100, "y": 200}
        sim.step()
        assert sim.io.s == 300


if __name__ == "__main__":
    print("Running test_struct_serialization...")
    test_struct_serialization()
    print("Running test_struct_methods...")
    test_struct_methods()
    print("ALL TESTS PASSED")
