"""
Elastic Streaming Pipeline Example using Stream[T]

Demonstrates:
1. Custom Packet struct streaming over Stream[Packet].
2. Producer (Source) generating data with valid signals.
3. TransformStage performing computation with elastic backpressure.
4. Consumer (Sink) accepting packets and displaying results.
"""

from nexhdl import *


# 1. Define Typed Packet Payload
class Packet(Struct):
    tag:  Logic[8]
    data: Logic[24]


# 2. Stage 1: Stream Producer (Source)
class PacketSource(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    out: OUTPUT[Stream[Packet]]

    def build(self, io):
        cnt = Reg[Logic[24]](init=1)
        
        # Drive output stream
        pkt = Packet(tag=Logic[8](0xAA), data=cnt)
        io.out.push(pkt, enable=1)
        
        with io.clk.posedge, io.rst.negedge:
            # Advance counter when handshake fires
            cnt.next = Mux[Logic[24]](io.out.fire, cnt + 1, cnt)


# 3. Stage 2: Elastic Transform Stage (Multiplies data payload by 10)
class TransformStage(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    inp: INPUT[Stream[Packet]]
    out: OUTPUT[Stream[Packet]]

    def build(self, io):
        # Register stage
        tag_reg   = Reg[Logic[8]](init=0)
        data_reg  = Reg[Logic[24]](init=0)
        valid_reg = Reg[Logic[1]](init=0)

        # Elastic flow control
        can_accept = io.out.ready | ~valid_reg
        io.inp.ready = can_accept

        # Output driving
        out_pkt = Packet(tag=tag_reg, data=data_reg)
        io.out.valid = valid_reg
        io.out.data  = out_pkt

        # Handshake events
        in_fire  = io.inp.fire
        out_fire = io.out.fire

        with io.clk.posedge, io.rst.negedge:
            # Latch transformed payload on input fire
            tag_reg.next  = Mux[Logic[8]](in_fire, io.inp.data.tag, tag_reg)
            data_reg.next = Mux[Logic[24]](in_fire, (io.inp.data.data * 10).trunc(24), data_reg)
            
            # Next valid logic
            next_valid = Mux[Logic[1]](
                in_fire,
                Logic[1](1),
                Mux[Logic[1]](out_fire, Logic[1](0), valid_reg)
            )
            valid_reg.next = next_valid


# 4. Stage 3: Top-Level Pipeline
class StreamPipelineTop(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    
    # Downstream flow control & sink output
    sink_ready: INPUT[Logic[1]]
    sink_tag:   OUTPUT[Logic[8]]
    sink_data:  OUTPUT[Logic[24]]
    sink_valid: OUTPUT[Logic[1]]

    def build(self, io):
        ready_wire = Wire[Logic[1]]()
        
        # Instantiate Source and Transform stage
        src = PacketSource(clk=io.clk, rst=io.rst, out_ready=ready_wire)
        txf = TransformStage(
            clk=io.clk,
            rst=io.rst,
            inp_valid=src.out_valid,
            inp_data=src.out_data,
            out_ready=io.sink_ready
        )
        ready_wire.assign = txf.inp_ready

        # Connect to Top-level output
        io.sink_tag   = txf.out_data.tag
        io.sink_data  = txf.out_data.data
        io.sink_valid = txf.out_valid


def main():
    print("Compiling StreamPipelineTop...")
    top = StreamPipelineTop()
    print("\nGenerated Verilog:")
    print("-" * 50)
    print(top.verilog())
    print("-" * 50)

    # Run JIT Simulation
    print("\nRunning Arcilator JIT Simulation:")
    with top.simulate() as sim:
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1
        sim.io.sink_ready = 1

        for cycle in range(1, 6):
            sim.tick()
            valid = sim.io.sink_valid
            tag = hex(sim.io.sink_tag)
            data = sim.io.sink_data
            print(f"Cycle {cycle}: Valid={valid} | Tag={tag} | Data={data}")


if __name__ == "__main__":
    main()
