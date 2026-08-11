from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Fifo, Struct

class Packet(Struct):
    data: Logic[32]
    id:   Logic[32]

class PacketBuffer(Module):
    """
    A FIFO buffer for Packet structs.
    """
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    push:     INPUT[Logic[1]]
    pop:      INPUT[Logic[1]]
    pkt_in:   INPUT[Packet]
    pkt_out:  OUTPUT[Packet]
    full:     OUTPUT[Logic[1]]
    empty:    OUTPUT[Logic[1]]

    def build(self, io):
        # Create a FIFO of Packets
        fifo = Fifo[16, Packet]()

        with io.clk.posedge, io.rst.negedge:
            fifo.push(io.pkt_in, io.push)
            io.pkt_out = fifo.pop(io.pop)

        io.full = fifo.full
        io.empty = fifo.empty

if __name__ == "__main__":
    dut = PacketBuffer()
    print(dut.verilog())

    with dut.simulate() as sim:
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1

        # Push a packet
        sim.io.pkt_in = {"data": 0xDEADBEEF, "id": 1}
        sim.io.push = 1
        sim.tick()
        sim.io.push = 0
        
        # Pop it
        sim.io.pop = 1
        sim.tick()
        print(f"Popped Packet: {sim.io.pkt_out}")
