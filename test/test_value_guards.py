from collections.abc import Iterable
import circt.ir
import pytest

from nexhdl import (
    Array,
    Clock,
    Fifo,
    INPUT,
    Logic,
    Map,
    Mem,
    Module,
    Mux,
    OUTPUT,
    Reg,
    Reset,
    Struct,
    Union,
    Wire,
)


class _Point(Struct):
    x: Logic[8]
    y: Logic[8]


class _Packet(Union):
    raw: Logic[16]
    point: _Point


def test_bool_raises_on_logic_in_module():
    class BadIfModule(Module):
        cond: INPUT[Logic[1]]
        a: INPUT[Logic[8]]
        b: INPUT[Logic[8]]
        out: OUTPUT[Logic[8]]

        def build(self, io):
            if io.cond:
                io.out = io.a
            else:
                io.out = io.b

    with pytest.raises(TypeError, match=r"Use Mux/&/\| for hardware conditions"):
        BadIfModule().compile()


def test_and_or_not_comparison_raise_on_logic():
    class BadOpsModule(Module):
        a: INPUT[Logic[1]]
        b: INPUT[Logic[1]]
        out: OUTPUT[Logic[1]]

        def build(self, io):
            io.out = io.a and io.b

    class BadOrModule(Module):
        a: INPUT[Logic[1]]
        b: INPUT[Logic[1]]
        out: OUTPUT[Logic[1]]

        def build(self, io):
            io.out = io.a or io.b

    class BadNotModule(Module):
        a: INPUT[Logic[1]]
        out: OUTPUT[Logic[1]]

        def build(self, io):
            io.out = not io.a

    class BadEqIfModule(Module):
        a: INPUT[Logic[8]]
        b: INPUT[Logic[8]]
        out: OUTPUT[Logic[8]]

        def build(self, io):
            if io.a == io.b:
                io.out = io.a
            else:
                io.out = io.b

    for mod_cls in (BadOpsModule, BadOrModule, BadNotModule, BadEqIfModule):
        with pytest.raises(TypeError, match=r"Use Mux/&/\| for hardware conditions"):
            mod_cls().compile()


def test_bool_raises_across_all_nex_values():
    module = circt.ir.Module.create()
    with circt.ir.InsertionPoint(module.body):
        logic_val = Logic[8](1)
        logic_zero = Logic[8](0)
        arr_val = Array[2, Logic[8]]([0, 1])
        struct_val = _Point(x=0, y=1)
        union_val = _Packet(raw=0)
        clk_val = Clock(Logic[1](0))
        rst_val = Reset(Logic[1](0))
        reg_val = Reg[Logic[1]](init=0)
        wire_val = Wire[Logic[1]]()
        map_val = Map[2, 8]((0, 1), default=0)

        for val in (
            logic_val,
            logic_zero,
            arr_val,
            struct_val,
            union_val,
            clk_val,
            rst_val,
            reg_val,
            wire_val,
            map_val,
        ):
            with pytest.raises(TypeError, match=r"Use Mux/&/\| for hardware conditions"):
                bool(val)


def test_logic_len_and_iteration_blocked():
    module = circt.ir.Module.create()
    with circt.ir.InsertionPoint(module.body):
        val = Logic[8](0x5A)
        reg_val = Reg[Logic[8]]()

        assert val.width == 8
        assert reg_val.width == 8
        assert not isinstance(val, Iterable)

        with pytest.raises(TypeError, match=r"Use \.width for bit width of Logic"):
            len(val)

        with pytest.raises(TypeError, match=r"Use \.width for bit width of Logic"):
            len(reg_val)

        with pytest.raises(TypeError, match="not iterable"):
            iter(val)

        with pytest.raises(TypeError, match="not iterable"):
            list(val)


def test_array_len_and_iteration_still_work():
    module = circt.ir.Module.create()
    with circt.ir.InsertionPoint(module.body):
        arr = Array[4, Logic[8]]([1, 2, 3, 4])
        assert len(arr) == 4
        assert len(list(arr)) == 4
        with pytest.raises(TypeError, match=r"Use Mux/&/\| for hardware conditions"):
            bool(arr)


def test_primitives_with_reset_and_init_compile():
    class SequentialWithReset(Module):
        clk: INPUT[Clock]
        rst: INPUT[Reset]
        en: INPUT[Logic[1]]
        din: INPUT[Logic[8]]
        out_reg: OUTPUT[Logic[8]]
        out_fifo: OUTPUT[Logic[8]]
        out_mem: OUTPUT[Logic[8]]

        def build(self, io):
            reg = Reg[Logic[8]](init=0)
            fifo = Fifo[4, Logic[8]]()
            mem = Mem[4, Logic[8]]()

            with io.clk.posedge, io.rst.negedge:
                reg.next = Mux[Logic[8]](io.en, io.din, reg)
                fifo.push(io.din, io.en)
                mem.write(Logic[2](0), io.din, io.en)
                io.out_fifo = fifo.pop(io.en)
                io.out_mem = mem[Logic[2](0)]

            io.out_reg = reg

    m = SequentialWithReset()
    m.compile()
    assert "hw.module" in m.mlir()


if __name__ == "__main__":
    test_primitives_with_reset_and_init_compile()
    print('✅ All tests passed!')