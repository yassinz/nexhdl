from nexhdl import *
import sys



class ByteStruct(Struct):
    b0: Logic[8]
    b1: Logic[8]
    b2: Logic[8]
    b3: Logic[8]

class Instruction(Union):
    raw: Logic[32]
    bytes: ByteStruct
    # Array view
    array: Array[4, Logic[8]]



class UnionStructArrayTest(Module):
    # Inputs
    instr_in: INPUT[Logic[32]]
    
    # Outputs
    out_b0: OUTPUT[Logic[8]]
    out_b1: OUTPUT[Logic[8]]
    out_b2: OUTPUT[Logic[8]]
    out_b3: OUTPUT[Logic[8]]
    
    out_arr0: OUTPUT[Logic[8]]
    out_arr1: OUTPUT[Logic[8]]
    out_arr2: OUTPUT[Logic[8]]
    out_arr3: OUTPUT[Logic[8]]

    def build(self, io):
        # Cast Input (i32) -> Union
        insn = Instruction(io.instr_in)
        
        # Struct View
        io.out_b0 = insn.bytes.b0
        io.out_b1 = insn.bytes.b1
        io.out_b2 = insn.bytes.b2
        io.out_b3 = insn.bytes.b3
        
        # Array View
        io.out_arr0 = insn.array[0]
        io.out_arr1 = insn.array[1]
        io.out_arr2 = insn.array[2]
        io.out_arr3 = insn.array[3]


def test_combo():
    print("\n=== Test Union/Struct/Array Combo (Byte Aligned) ===")
    m = UnionStructArrayTest()
    m.compile()
    
    with Simulator(m.module, m.name) as sim:
        # Test Case: 0xAABBCCDD
        val = 0xAABBCCDD
        sim.io.instr_in = val
        sim.step()
        
        print(f"Input: {hex(val)}")
        print(f"B0: {hex(sim.io.out_b0)}")
        print(f"B1: {hex(sim.io.out_b1)}")
        print(f"B2: {hex(sim.io.out_b2)}")
        print(f"B3: {hex(sim.io.out_b3)}")
        
        print(f"Arr[0]: {hex(sim.io.out_arr0)}")
        print(f"Arr[1]: {hex(sim.io.out_arr1)}")
        print(f"Arr[2]: {hex(sim.io.out_arr2)}")
        print(f"Arr[3]: {hex(sim.io.out_arr3)}")
        
        # Both Struct and Array are now MSB-First, so they should match!
        assert sim.io.out_arr0 == 0xAA
        assert sim.io.out_arr1 == 0xBB
        assert sim.io.out_arr2 == 0xCC
        assert sim.io.out_arr3 == 0xDD

        assert sim.io.out_b0 == 0xAA
        assert sim.io.out_b1 == 0xBB
        assert sim.io.out_b2 == 0xCC
        assert sim.io.out_b3 == 0xDD
             
        print("Success! Verified Struct (MSB-First) and Array (MSB-First) alignment.")

if __name__ == "__main__":
    try:
        test_combo()
    except Exception as e:
        print(f"\nFAILURE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
