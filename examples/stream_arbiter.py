"""
Round-Robin 2-to-1 Stream Arbiter

Fairly merges two backpressure-capable input streams (inp_a and inp_b)
into a single output stream using round-robin arbitration.

Arbitration rules:
  - Grant to the preferred port when it has valid data.
  - Fall through to the other port when the preferred one is idle.
  - Advance the preference on every successful output transfer (fire).

This example demonstrates:
  - Multiple Stream[T] ports on one module (two inputs, one output)
  - The full StreamHandle API: .valid, .ready, .data, .fire, .push()
  - Parameterized modules (T can be any NexType)
  - Backpressure propagation
"""

from nexhdl import *


class StreamArbiter[T](Module):
    """
    Fair 2-to-1 round-robin stream arbiter with full backpressure support.

    Port map:
      inp_a_valid, inp_a_data  -> INPUT  (Stream A)
      inp_a_ready              -> OUTPUT (backpressure to A)
      inp_b_valid, inp_b_data  -> INPUT  (Stream B)
      inp_b_ready              -> OUTPUT (backpressure to B)
      out_valid,   out_data    -> OUTPUT (merged stream)
      out_ready                -> INPUT  (backpressure from downstream)
    """
    clk:   INPUT[Clock]
    rst:   INPUT[Reset]
    inp_a: INPUT[Stream[T]]
    inp_b: INPUT[Stream[T]]
    out:   OUTPUT[Stream[T]]

    def build(self, io):
        # 1-bit preference register: 0 = prefer A, 1 = prefer B
        prefer_b = Reg[Logic[1]](init=0)

        # Grant A when: A is valid AND (we prefer A OR B has nothing to offer)
        # Grant B when: B is valid AND (we prefer B OR A has nothing to offer)
        grant_a = io.inp_a.valid & (~prefer_b | ~io.inp_b.valid)
        grant_b = io.inp_b.valid & ( prefer_b | ~io.inp_a.valid)

        # Steer selected payload to output
        out_data  = Mux[T](grant_a, io.inp_a.data, io.inp_b.data)
        out_valid = grant_a | grant_b
        io.out.push(out_data, enable=out_valid)

        # Backpressure: only the winning port sees ready
        io.inp_a.ready = grant_a & io.out.ready
        io.inp_b.ready = grant_b & io.out.ready

        # Flip preference on every completed output handshake
        with io.clk.posedge, io.rst.negedge:
            prefer_b.next = Mux[Logic[1]](io.out.fire, ~prefer_b, prefer_b)


if __name__ == "__main__":
    print("=== StreamArbiter[Logic[16]] ===\n")

    arb = StreamArbiter[Logic[16]]()

    print("Generated Verilog:")
    print("-" * 60)
    print(arb.verilog())
    print("-" * 60)

    print("\nSimulation — Round-Robin Arbitration:\n")
    with arb.simulate() as sim:
        # Reset — keep out_ready=0 so the preference register doesn't
        # advance during reset and enters the test cleanly at prefer_b=0.
        sim.io.out_ready = 0
        sim.io.inp_a_valid = 0
        sim.io.inp_b_valid = 0
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1
        sim.tick()                       # one idle cycle to settle
        sim.io.out_ready = 1

        # ── Cycle 1: Both valid, preference=A ────────────────────────
        sim.io.inp_a_valid = 1;  sim.io.inp_a_data = 0xAAAA
        sim.io.inp_b_valid = 1;  sim.io.inp_b_data = 0xBBBB
        sim.step()                       # step: evaluate combinational, don't clock yet
        out = hex(sim.io.out_data)
        print(f"Cycle 1 | Both valid  (prefer A) -> out={out}  valid={sim.io.out_valid}")
        assert sim.io.out_data  == 0xAAAA, f"Expected 0xaaaa, got {out}"
        assert sim.io.out_valid == 1
        assert sim.io.inp_a_ready == 1   # A is granted
        assert sim.io.inp_b_ready == 0   # B is held off
        sim.tick()                       # clock: advance preference to B

        # ── Cycle 2: Both valid, preference now B ────────────────────
        sim.step()
        out = hex(sim.io.out_data)
        print(f"Cycle 2 | Both valid  (prefer B) -> out={out}  valid={sim.io.out_valid}")
        assert sim.io.out_data  == 0xBBBB, f"Expected 0xbbbb, got {out}"
        assert sim.io.out_valid == 1
        assert sim.io.inp_b_ready == 1   # B is granted
        assert sim.io.inp_a_ready == 0   # A is held off
        sim.tick()

        # ── Cycle 3: Only B valid — fall-through despite A preference ─
        sim.io.inp_a_valid = 0
        sim.step()
        out = hex(sim.io.out_data)
        print(f"Cycle 3 | Only B valid(prefer A) -> out={out}  valid={sim.io.out_valid}  (fall-through to B)")
        assert sim.io.out_data  == 0xBBBB, f"Expected 0xbbbb, got {out}"
        assert sim.io.out_valid == 1
        sim.tick()

        # ── Cycle 4: Only A valid — fall-through despite B preference ─
        sim.io.inp_a_valid = 1;  sim.io.inp_b_valid = 0
        sim.step()
        out = hex(sim.io.out_data)
        print(f"Cycle 4 | Only A valid(prefer B) -> out={out}  valid={sim.io.out_valid}  (fall-through to A)")
        assert sim.io.out_data  == 0xAAAA, f"Expected 0xaaaa, got {out}"
        assert sim.io.out_valid == 1
        sim.tick()

        # ── Cycle 5: Neither valid ────────────────────────────────────
        sim.io.inp_a_valid = 0
        sim.step()
        print(f"Cycle 5 | None valid             -> valid={sim.io.out_valid}  (output idle)")
        assert sim.io.out_valid == 0
        sim.tick()

        # ── Cycle 6: Backpressure — downstream not ready ─────────────
        sim.io.inp_a_valid = 1;  sim.io.inp_b_valid = 1
        sim.io.out_ready = 0
        sim.step()
        print(f"Cycle 6 | Both valid, out_ready=0 -> inp_a_ready={sim.io.inp_a_ready}  inp_b_ready={sim.io.inp_b_ready}  (stalled)")
        assert sim.io.inp_a_ready == 0   # no grant issued when downstream stalls
        assert sim.io.inp_b_ready == 0
        sim.tick()

    print("\n✓ StreamArbiter: all assertions passed!")
