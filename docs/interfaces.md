# Interfaces & Streams (ESI-Style)

NexHDL provides first-class support for hardware **Interfaces**, **Bundles**, and ready/valid **Streams** (modeled after CIRCT's Elastic Silicon Interconnect / ESI).

---

## 1. What is an Interface?

An `Interface` (or `Bundle`) groups related hardware signals into a reusable, direction-aware protocol. When used in module port declarations with `INPUT[...]` or `OUTPUT[...]`, NexHDL automatically assigns and flips signal polarities correctly.

---

## 2. Stream[T]

`Stream[T]` is the standard ready/valid handshaked streaming channel carrying any hardware payload type `T` (e.g. `Logic`, `Struct`, `Array`).

### Port Declaration

Use `INPUT[...]` for incoming streams and `OUTPUT[...]` for outgoing streams:

```python
from nexhdl import *

class StreamProcessor[WIDTH: int](Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    
    # Incoming stream (Consumer / Sink)
    # - inp_valid: INPUT
    # - inp_ready: OUTPUT
    # - inp_data:  INPUT
    inp: INPUT[Stream[Logic[WIDTH]]]
    
    # Outgoing stream (Producer / Source)
    # - out_valid: OUTPUT
    # - out_ready: INPUT
    # - out_data:  OUTPUT
    out: OUTPUT[Stream[Logic[WIDTH]]]

    def build(self, io):
        # Backpressure: accept input when output is ready
        io.inp.ready = io.out.ready
        
        # Drive output stream
        io.out.push(io.inp.data * 2, enable=io.inp.valid)
```

---

## 3. Stream API Reference

When you access an interface port inside `build(self, io)` (e.g., `io.inp` or `io.out`), you interact with a `StreamHandle` offering the following capabilities:

| Property / Method | Description |
| :--- | :--- |
| `stream.data` | Access the payload signal (`NexValue`). |
| `stream.valid` | Valid signal (`Logic[1]`). |
| `stream.ready` | Ready signal (`Logic[1]`). |
| `stream.fire` | Returns `valid & ready` (1-bit `Logic`), indicating a completed handshake transfer. |
| `stream.push(data, [enable])` | Sets `stream.valid = enable` (default 1) and assigns `stream.data = data`. |
| `stream.pop([enable])` | Sets `stream.ready = enable` (default 1) and returns `stream.data`. |
| `stream.connect(other)` | Connects a stream source to a stream sink (wires valid, data forward and ready backward). |
| `src >> dst` | Pipe operator syntax for `src.connect(dst)`. |

---

## 4. Custom Interfaces & Bundles

You can define your own domain-specific protocols by subclassing `Interface` (or `Bundle`):

```python
from nexhdl import *

class MemoryRequest(Struct):
    addr: Logic[32]
    wdata: Logic[32]
    we: Logic[1]

# Custom Bidirectional Memory Bus Interface
class MemoryBus(Interface):
    req_valid: OUTPUT[Logic[1]]
    req_ready: INPUT[Logic[1]]
    req_data:  OUTPUT[MemoryRequest]
    
    resp_valid: INPUT[Logic[1]]
    resp_data:  INPUT[Logic[32]]

class MemoryClient(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    mem: OUTPUT[MemoryBus]  # Outgoing (Master) interface

class MemoryServer(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    mem: INPUT[MemoryBus]   # Incoming (Slave) interface — polarities flipped automatically!
```

---

## 5. Streaming with Custom Struct Payloads

`Stream[T]` seamlessly accepts composite types like `Struct`:

```python
class Packet(Struct):
    tag:  Logic[8]
    data: Logic[24]

class PacketFilter(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    rx:  INPUT[Stream[Packet]]
    tx:  OUTPUT[Stream[Packet]]

    def build(self, io):
        # Access structured fields directly
        tag = io.rx.data.tag
        data = io.rx.data.data
        
        # Only pass packets with tag == 0xAA
        pass_packet = (tag == 0xAA)
        
        io.tx.push(io.rx.data, enable=io.rx.valid & pass_packet)
        io.rx.ready = io.tx.ready | ~pass_packet
```

---

## 6. Internal Channels (`StreamChannel`)

To connect internal submodules or create point-to-point queues inside a `build()` method, use `StreamChannel[T]`:

```python
class StreamingSystem(Module):
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    out: OUTPUT[Stream[Logic[32]]]

    def build(self, io):
        # Create an internal streaming channel wire
        chan = StreamChannel[Logic[32]]()
        
        # Module 1 drives channel
        mod1 = ProducerModule(clk=io.clk, rst=io.rst, out_ready=chan.inp.ready)
        chan.inp.valid = mod1.out_valid
        chan.inp.data  = mod1.out_data
        
        # Channel drives Module 2
        mod2 = ConsumerModule(clk=io.clk, rst=io.rst, inp_valid=chan.out.valid, inp_data=chan.out.data)
        chan.out.ready = mod2.inp_ready
```

---

## 7. Generated Verilog Mapping

Interface ports flatten into standard, predictable Verilog signals prefixed by the port name:

```verilog
module StreamProcessor(
  input         clk,
                rst,
                inp_valid,
  input  [31:0] inp_data,
  input         out_ready,
  output        inp_ready,
                out_valid,
  output [31:0] out_data
);
  assign inp_ready = out_ready;
  assign out_valid = inp_valid;
  assign out_data = inp_data * 32'h2;
endmodule
```
