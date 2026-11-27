"""
Fully pipelined streaming radix-2 FFT in NexHDL.

One complete N-point complex frame enters EVERY clock cycle and one leaves
every clock cycle, after a latency of log2(N) cycles.

What this shows off
  * Generic Struct with operator overloading: Complex[W] defines + and - so the
    butterfly reads like the math (a + t, a - t).  Both operators include the
    1/2 per-stage scaling, so they can never overflow.
  * Types compose: Array[N, Complex[W]] is a port, a register and a cast target.
  * Elaboration-time generation: bit-reversal wiring, the butterfly network,
    twiddle factors (computed with Python's math module) and trivial-twiddle
    pruning are all decided by Python at build time -> pure parallel hardware.
  * Q1.(W-1) fixed-point complex multiply with a reusable saturator.
  * Valid-bit pipeline carried alongside the data.
  * Param validator (N must be a power of two).

Output scaling: Y[k] = DFT(x)[k] / N   (1/2 per stage, log2(N) stages).
"""
import math
from nexhdl import *

PowerOf2 = Param[int](lambda x: x >= 2 and (x & (x - 1)) == 0, "Must be power of 2 (>= 2)")


# --------------------------------------------------------------------------
# Complex number type with overloaded (scaled) arithmetic
# --------------------------------------------------------------------------
class Complex[W: int](Struct):
    re: Logic[W]   # first field -> most significant bits
    im: Logic[W]

    def __add__(self, other):
        """(self + other) / 2, exact (W+1 bit sum, drop LSB)."""
        sr = Logic[W + 1](self.re.sext(W + 1).si + other.re.sext(W + 1).si)
        si = Logic[W + 1](self.im.sext(W + 1).si + other.im.sext(W + 1).si)
        return Complex[W](re=sr[1:W + 1], im=si[1:W + 1])

    def __sub__(self, other):
        """(self - other) / 2, exact (W+1 bit difference, drop LSB)."""
        dr = Logic[W + 1](self.re.sext(W + 1).si - other.re.sext(W + 1).si)
        di = Logic[W + 1](self.im.sext(W + 1).si - other.im.sext(W + 1).si)
        return Complex[W](re=dr[1:W + 1], im=di[1:W + 1])


# --------------------------------------------------------------------------
# Elaboration-time helpers (they return hardware, they are not hardware)
# --------------------------------------------------------------------------
def saturate(x, IN_W, OUT_W):
    """Clip a signed IN_W-bit value to OUT_W bits using sign-bit range checks."""
    sign = x[IN_W - 1]
    n = IN_W - OUT_W + 1
    top = x[OUT_W - 1:IN_W]                       # bits OUT_W-1 .. IN_W-1
    all_ones = top == Logic[n]((1 << n) - 1)
    all_zeros = top == Logic[n](0)
    in_range = Mux[Logic[1]](sign, all_ones, all_zeros)
    max_pos = Logic[OUT_W]((1 << (OUT_W - 1)) - 1)
    max_neg = Logic[OUT_W](1 << (OUT_W - 1))
    clipped = Mux[Logic[OUT_W]](sign, max_neg, max_pos)
    return Mux[Logic[OUT_W]](in_range, x.trunc(OUT_W), clipped)


def cmul_const(b, wr, wi, W):
    """b * (wr + j*wi) where wr/wi are Q1.(W-1) integer constants."""
    PW = 2 * W + 1
    M = (1 << PW) - 1
    br = b.re.sext(PW).si
    bi = b.im.sext(PW).si
    cr = Logic[PW](wr & M).si
    ci = Logic[PW](wi & M).si
    re = Logic[PW](Logic[PW](br * cr).si - Logic[PW](bi * ci).si)
    im = Logic[PW](Logic[PW](br * ci).si + Logic[PW](bi * cr).si)
    # Rescale by 2^-(W-1): keep bits [W-1 .. PW-1] (W+2 bits), then saturate to W.
    return Complex[W](re=saturate(re[W - 1:PW], W + 2, W),
                      im=saturate(im[W - 1:PW], W + 2, W))


def twiddle(j, m, W):
    """exp(-2*pi*i*j/m) quantised to Q1.(W-1)."""
    scale = (1 << (W - 1)) - 1
    ang = -2.0 * math.pi * j / m
    return round(math.cos(ang) * scale), round(math.sin(ang) * scale)


def bit_reverse(i, bits):
    return int(format(i, "0{}b".format(bits))[::-1], 2)


# --------------------------------------------------------------------------
# The FFT
# --------------------------------------------------------------------------
class StreamingFFT[N: PowerOf2, W: int](Module):
    clk:       INPUT[Clock]
    rst:       INPUT[Reset]
    in_valid:  INPUT[Logic[1]]
    x:         INPUT[Array[N, Complex[W]]]
    y:         OUTPUT[Array[N, Complex[W]]]
    out_valid: OUTPUT[Logic[1]]

    def build(self, io):
        L = clog2(N)

        # Decimation-in-time: bit-reversed input order is just wiring.
        cur = [io.x[bit_reverse(i, L)] for i in range(N)]
        valid = io.in_valid

        for s in range(L):                       # one pipeline stage per level
            m = 2 << s
            half = m >> 1
            nxt = [None] * N

            for k in range(0, N, m):             # every butterfly, in parallel
                for j in range(half):
                    a = cur[k + j]
                    b = cur[k + j + half]

                    # Elaboration-time pruning: twiddle 1+0j needs no multiplier.
                    if j == 0:
                        t = b
                    else:
                        wr, wi = twiddle(j, m, W)
                        t = cmul_const(b, wr, wi, W)

                    nxt[k + j] = a + t           # Complex.__add__  (÷2)
                    nxt[k + j + half] = a - t    # Complex.__sub__  (÷2)

            stage = Reg[Array[N, Complex[W]]]()
            v_reg = Reg[Logic[1]](init=0)
            with io.clk.posedge, io.rst.negedge:
                stage.next = Array[N, Complex[W]](nxt)
                v_reg.next = valid

            cur = [stage[i] for i in range(N)]
            valid = v_reg

        io.y = Array[N, Complex[W]](cur)
        io.out_valid = valid


# --------------------------------------------------------------------------
# Testbench
# --------------------------------------------------------------------------
def to_signed(v, w):
    return v - (1 << w) if v & (1 << (w - 1)) else v


def pack(frame, W):
    mask = (1 << W) - 1
    return [{"re": int(round(z.real)) & mask, "im": int(round(z.imag)) & mask} for z in frame]


def unpack(frame, W):
    return [complex(to_signed(e["re"], W), to_signed(e["im"], W)) for e in frame]


def golden(frame, N):
    """Floating-point DFT / N of the (already quantised) input frame."""
    return [sum(frame[n] * complex(math.cos(2 * math.pi * k * n / N),
                                   -math.sin(2 * math.pi * k * n / N))
                for n in range(N)) / N
            for k in range(N)]


def stream(sim, frames, W, flush):
    """Feed one frame per clock; return (outputs, first_valid_tick)."""
    outs, first = [], None
    tick = 0
    for fr in list(frames) + [None] * flush:
        if fr is None:
            sim.io.in_valid = 0
        else:
            sim.io.in_valid = 1
            sim.io.x = pack(fr, W)
        sim.tick()
        if sim.io.out_valid:
            if first is None:
                first = tick
            outs.append(unpack(sim.io.y, W))
        tick += 1
    return outs, first


if __name__ == "__main__":
    import cmath
    import random

    N, W = 16, 16
    L = clog2(N)
    dut = StreamingFFT[N, W]()

    with dut.simulate() as sim:
        sim.io.rst = 0; sim.io.in_valid = 0; sim.tick(); sim.io.rst = 1
        sim.io.x = pack([0] * N, W)

        # Test 1: pure complex tone in bin 3 -> energy in exactly one bin
        A = 16000
        tone = [A * cmath.exp(2j * math.pi * 3 * n / N) for n in range(N)]
        outs, first = stream(sim, [tone], W, flush=L + 2)
        mags = [abs(z) for z in outs[0]]
        peak = max(range(N), key=lambda k: mags[k])
        print("tone      : peak bin = %d, |Y[3]| = %.1f (ideal %d)" % (peak, mags[3], A))
        assert peak == 3
        assert all(m < 8 for k, m in enumerate(mags) if k != 3)

        # Test 2: back-to-back random frames, one per clock, vs float DFT
        random.seed(1)
        frames = [[complex(random.randint(-20000, 20000), random.randint(-20000, 20000))
                   for _ in range(N)] for _ in range(24)]
        outs, first = stream(sim, frames, W, flush=L + 2)
        assert len(outs) == len(frames), "one output frame per input frame"

        worst, sig, noise = 0.0, 0.0, 0.0
        for fr, out in zip(frames, outs):
            q = [complex(round(z.real), round(z.imag)) for z in fr]
            ref = golden(q, N)
            for r, o in zip(ref, out):
                e = abs(r - o)
                worst = max(worst, e)
                sig += abs(r) ** 2
                noise += e ** 2
        snr = 10 * math.log10(sig / noise)
        print("streaming : %d frames, latency %d clk, worst error %.2f LSB, SNR %.1f dB"
              % (len(outs), first, worst, snr))
        assert worst < 6.0

        # Test 3: full-scale input exercises the saturating twiddle multiplier
        full = [complex(32767, -32768) if n % 2 else complex(-32768, 32767) for n in range(N)]
        outs, _ = stream(sim, [full], W, flush=L + 2)
        ref = golden([complex(round(z.real), round(z.imag)) for z in full], N)
        err = max(abs(r - o) for r, o in zip(ref, outs[0]))
        print("full scale: worst error %.2f LSB" % err)
        assert err < 6.0

    print("All tests passed.")
