import pytest
from nexhdl import *

__test__ = True


def test_interface_definition():
    """Test custom Interface/Bundle definition and direction roles."""
    class CustomBundle(Interface):
        valid: OUTPUT[Logic[1]]
        ready: INPUT[Logic[1]]
        data:  OUTPUT[Logic[32]]

    # Check roles via INPUT and OUTPUT
    out_port = OUTPUT[CustomBundle]
    in_port  = INPUT[CustomBundle]
    assert not out_port.is_flipped
    assert in_port.is_flipped

    # Check flattened ports
    flattened_prod = out_port.get_flattened_ports("tx")
    assert len(flattened_prod) == 3
    port_dict_prod = {name: (dir, typ) for name, dir, typ in flattened_prod}
    assert "tx_valid" in port_dict_prod
    assert "tx_ready" in port_dict_prod
    assert "tx_data" in port_dict_prod


def test_stream_module_ports():
    """Test using Stream inside INPUT[...] and OUTPUT[...] on Module ports."""
    class Passthrough(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        in_stream:  INPUT[Stream[Logic[16]]]
        out_stream: OUTPUT[Stream[Logic[16]]]

        def build(self, io):
            # Connect in_stream to out_stream directly
            io.out_stream.valid = io.in_stream.valid
            io.out_stream.data  = io.in_stream.data + 1
            io.in_stream.ready  = io.out_stream.ready

    mod = Passthrough()
    verilog = mod.verilog()
    assert "in_stream_valid" in verilog
    assert "in_stream_ready" in verilog
    assert "in_stream_data" in verilog
    assert "out_stream_valid" in verilog
    assert "out_stream_ready" in verilog
    assert "out_stream_data" in verilog


def test_stream_simulation_handshake():
    """Simulate a streaming producer-consumer with backpressure."""
    class StreamAdder(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        in_stream:  INPUT[Stream[Logic[32]]]
        out_stream: OUTPUT[Stream[Logic[32]]]

        def build(self, io):
            # Simple registered stage
            data_reg = Reg[Logic[32]](init=0)
            valid_reg = Reg[Logic[1]](init=0)

            # We accept input if output is ready or we are not holding valid data
            can_accept = io.out_stream.ready | ~valid_reg
            io.in_stream.ready = can_accept

            io.out_stream.valid = valid_reg
            io.out_stream.data = data_reg

            # Fire conditions
            in_fire = io.in_stream.fire
            out_fire = io.out_stream.fire

            with io.clk.posedge, io.rst.negedge:
                # Latch new data on fire
                data_reg.next = Mux[Logic[32]](in_fire, io.in_stream.data * 2, data_reg)
                
                # Next valid calculation
                next_valid = Mux[Logic[1]](
                    in_fire,
                    Logic[1](1),
                    Mux[Logic[1]](out_fire, Logic[1](0), valid_reg)
                )
                valid_reg.next = next_valid

    dut = StreamAdder()
    with dut.simulate() as sim:
        # Reset
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1

        # Cycle 1: Send 10 into stream, downstream consumer is NOT ready
        sim.io.in_stream_valid = 1
        sim.io.in_stream_data = 10
        sim.io.out_stream_ready = 0
        sim.tick()

        # Cycle 2: Data latched into adder stage (valid_out should now be 1, out_data = 20)
        assert sim.io.out_stream_valid == 1
        assert sim.io.out_stream_data == 20
        # in_stream should NOT accept new data because valid_reg is full and out_ready is 0
        assert sim.io.in_stream_ready == 0

        # Cycle 3: Consumer asserts ready
        sim.io.out_stream_ready = 1
        sim.io.in_stream_valid = 0
        sim.tick()

        # Cycle 4: Data accepted by downstream, valid drops
        assert sim.io.out_stream_valid == 0


def test_parameterized_stream_struct():
    """Test Stream carrying custom Struct payloads inside INPUT/OUTPUT."""
    class Pixel(Struct):
        r: Logic[8]
        g: Logic[8]
        b: Logic[8]

    class PixelPipeline(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        rx: INPUT[Stream[Pixel]]
        tx: OUTPUT[Stream[Pixel]]

        def build(self, io):
            # Transform RGB -> Grayscale on stream
            r = io.rx.data.r
            g = io.rx.data.g
            b = io.rx.data.b
            
            gray_data = Pixel(r=r, g=g, b=b)
            
            io.tx.push(gray_data, enable=io.rx.valid)
            io.rx.ready = io.tx.ready

    mod = PixelPipeline()
    verilog = mod.verilog()
    assert "rx_data" in verilog
    assert "tx_data" in verilog


def test_stream_connect_syntax():
    """Test .connect() and >> stream piping operator."""
    class PipeStage(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        inp: INPUT[Stream[Logic[32]]]
        out: OUTPUT[Stream[Logic[32]]]

        def build(self, io):
            # Forward stream using pipe operator
            io.inp >> io.out

    mod = PipeStage()
    with mod.simulate() as sim:
        sim.io.inp_valid = 1
        sim.io.inp_data = 42
        sim.io.out_ready = 1
        sim.step()

        assert sim.io.out_valid == 1
        assert sim.io.out_data == 42
        assert sim.io.inp_ready == 1


def test_stream_channel_internal():
    """Test StreamChannel between internal modules/wires."""
    class ProducerMod(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        out: OUTPUT[Stream[Logic[32]]]

        def build(self, io):
            cnt = Reg[Logic[32]](init=100)
            io.out.push(cnt, enable=1)
            with io.clk.posedge, io.rst.negedge:
                cnt.next = Mux[Logic[32]](io.out.fire, cnt + 1, cnt)

    class ConsumerMod(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        inp: INPUT[Stream[Logic[32]]]
        received: OUTPUT[Logic[32]]

        def build(self, io):
            reg_val = Reg[Logic[32]](init=0)
            io.inp.pop(enable=1)
            io.received = reg_val
            with io.clk.posedge, io.rst.negedge:
                reg_val.next = Mux[Logic[32]](io.inp.fire, io.inp.data, reg_val)

    class Top(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        result: OUTPUT[Logic[32]]

        def build(self, io):
            ready_wire = Wire[Logic[1]]()
            prod = ProducerMod(clk=io.clk, rst=io.rst, out_ready=ready_wire)
            cons = ConsumerMod(clk=io.clk, rst=io.rst, inp_valid=prod.out_valid, inp_data=prod.out_data)
            ready_wire.assign = cons.inp_ready

            io.result = cons.received

    top = Top()
    with top.simulate() as sim:
        sim.io.rst = 0; sim.tick(); sim.io.rst = 1
        sim.tick()
        assert sim.io.result == 100
        sim.tick()
        assert sim.io.result == 101



def test_circt_esi_channel_integration():
    """Test direct CIRCT ESI dialect type and channel integration."""
    from circt.dialects import esi
    ctx = get_context()
    with ctx:
        esi_type = Stream[Logic[32]].to_esi_channel_type()
        assert isinstance(esi_type, esi.ChannelType)
        assert "!esi.channel<i32>" in str(esi_type)


if __name__ == "__main__":
    test_interface_definition()
    test_stream_module_ports()
    test_stream_simulation_handshake()
    test_parameterized_stream_struct()
    test_stream_connect_syntax()
    test_stream_channel_internal()
    test_circt_esi_channel_integration()
    