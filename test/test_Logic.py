from nexhdl import *
from random import randrange





class LogicTestOperations[WIDTH: int](Module):
    a:     INPUT[Logic[WIDTH]]
    b:     INPUT[Logic[WIDTH]]

    out_add: OUTPUT[Logic[WIDTH]]
    out_mul: OUTPUT[Logic[WIDTH]]
    out_and: OUTPUT[Logic[WIDTH]]
    out_or : OUTPUT[Logic[WIDTH]]
    out_xor: OUTPUT[Logic[WIDTH]]
    out_sub: OUTPUT[Logic[WIDTH]]
    out_div: OUTPUT[Logic[WIDTH]]
    out_mod: OUTPUT[Logic[WIDTH]]
    out_lshift: OUTPUT[Logic[WIDTH]]
    out_rshift: OUTPUT[Logic[WIDTH]]
    out_eq  : OUTPUT[Logic[1]]
    out_ne  : OUTPUT[Logic[1]]
    out_lt  : OUTPUT[Logic[1]]
    out_le  : OUTPUT[Logic[1]]
    out_gt  : OUTPUT[Logic[1]]
    out_ge  : OUTPUT[Logic[1]]
    out_neg : OUTPUT[Logic[WIDTH]]
    out_inv : OUTPUT[Logic[WIDTH]]
    out_pos : OUTPUT[Logic[WIDTH]]
    out_concat: OUTPUT[Logic[WIDTH*2]]
    out_sext : OUTPUT[Logic[WIDTH+1]]
    out_zext : OUTPUT[Logic[WIDTH+1]]
    out_trunc : OUTPUT[Logic[WIDTH//2]]
    out_replicate: OUTPUT[Logic[WIDTH*2]]
    out_getbit: OUTPUT[Logic[1]]
    out_slice: OUTPUT[Logic[WIDTH//2]]
    out_parity: OUTPUT[Logic[1]]
    out_reverse: OUTPUT[Logic[WIDTH]]

    
    def build(self, io):
        io.out_add = io.a + io.b
        io.out_mul = io.a * io.b
        io.out_and = io.a & io.b
        io.out_or  = io.a | io.b
        io.out_xor = io.a ^ io.b
        io.out_sub = io.a - io.b
        io.out_div = io.a / io.b
        io.out_mod = io.a % io.b
        io.out_lshift = io.a << 2
        io.out_rshift = io.a >> 2
        io.out_eq  = io.a == io.b
        io.out_ne  = io.a != io.b
        io.out_lt  = io.a < io.b
        io.out_le  = io.a <= io.b
        io.out_gt  = io.a > io.b
        io.out_ge  = io.a >= io.b
        io.out_neg = -io.a
        io.out_inv = ~io.a
        io.out_pos = +io.a
        io.out_concat = io.a @ io.b
        io.out_sext = io.a.sext(io.a.width + 1)
        io.out_zext = io.a.zext(io.a.width + 1)
        io.out_trunc = io.a.trunc(io.a.width//2)
        io.out_replicate = io.a.replicate(2)
        io.out_getbit = io.a[2]
        io.out_slice = io.a[4:20]
        io.out_parity = io.a.parity()
        io.out_reverse = io.a.reverse()


def test_Logic_operations():
    WIDTH = 32
    module = LogicTestOperations[WIDTH]()
    #print(module.verilog())
    with module.simulate() as sim:
        io = sim.io
        A, B = 0xabcdbeff, 0x12345678
        io.a, io.b = A, B
        
        mask = 0xffffffff

        sim.step()
        assert io.out_add == (A + B) & mask
        assert io.out_mul == (A * B) & mask
        assert io.out_and == (A & B) & mask
        assert io.out_or  == (A | B) & mask
        assert io.out_xor == (A ^ B) & mask
        assert io.out_sub == (A - B) & mask
        assert io.out_div == (A // B) & mask
        assert io.out_mod == (A % B) & mask
        assert io.out_lshift == (A << 2) & mask
        assert io.out_rshift == (A >> 2) & mask
        assert io.out_eq == (A == B)
        assert io.out_ne == (A != B)
        assert io.out_lt == (A < B)
        assert io.out_le == (A <= B)
        assert io.out_gt == (A > B)
        assert io.out_ge == (A >= B)
        assert io.out_neg == (-A) & mask
        assert io.out_inv == (~A) & mask
        assert io.out_pos == (+A) & mask
        assert io.out_concat == ((A << 32) | B)
        assert io.out_sext == ((A & (1<<31)) >>31) * (1<<32) | A 
        assert io.out_zext ==  A
        assert io.out_trunc == A & 0xffff
        
        assert io.out_replicate == (A << 32) | A
        assert io.out_getbit == ((A >> 2) & 1)
        assert io.out_slice == ((A >> 4) & 0xffff)

        assert io.out_parity == A.bit_count() & 1
        assert io.out_reverse == int(bin(A)[2:].zfill(WIDTH)[::-1], 2)
        


class TestReverse(Module):
    a: INPUT[Logic[32]]
    b: INPUT[Logic[32]]
    c: INPUT[Logic[32]]
    out0: OUTPUT[Logic[32]]
    out1: OUTPUT[Logic[32]]
    

    def build(self, io):
        io.out0 = (io.b.reverse() | io.a.reverse()).reverse()
        io.out1 = io.c.reverse()


def test_reverse():
    module = TestReverse()
    module.compile()
    with Simulator(module.module, module.name) as sim:
        io = sim.io
        A, B, C = 0xabcdbeff, 0x12345678, 0b10000000_00000000_00000000_00000000
        io.a, io.b, io.c = A, B, C
        sim.step()
        assert io.out0 == 3153985279
        assert io.out1 == 1





if __name__ == "__main__":
    test_reverse()
    test_Logic_operations()
