from nexhdl import *
from random import randrange



class Adder[WIDTH: int](Module):
    a: INPUT[Logic[WIDTH]]
    b: INPUT[Logic[WIDTH]]
    out: OUTPUT[Logic[WIDTH]]

    def build(self, io):
        io.out = io.a + io.b
    

class Multiplier[WIDTH: int](Module):
    a: INPUT[Logic[WIDTH]]
    b: INPUT[Logic[WIDTH]]
    out: OUTPUT[Logic[WIDTH]]

    def build(self, io):
        io.out = io.a * io.b


class AddMul[WIDTH: int](Module):
    a: INPUT[Logic[WIDTH]]
    b: INPUT[Logic[WIDTH]]
    c: INPUT[Logic[WIDTH]]
    out: OUTPUT[Logic[WIDTH]]

    def build(self, io):
        adder = Adder[WIDTH](a=io.a, b=io.b)
        mult = Multiplier[WIDTH](a=adder.out, b=io.c)
        io.out = mult.out


def test_add_mul():
    add_mul = AddMul[512]()
    add_mul.compile()
    
    with Simulator(add_mul.module, add_mul.name) as sim:
        io = sim.io
        for i in range(10):
            io.a = 10
            io.b = i
            io.c = i
            sim.step()
            print(io.out)




if __name__ == "__main__":
    test_add_mul()    
