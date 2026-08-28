"""CIRCT IR transformations and lowering passes"""

from circt.passmanager import PassManager
import circt
from circt.support import _walk_with_filter as walk_with_filter
from circt.ir import WalkResult, WalkOrder
from circt.dialects import hw, seq, llvm
from .states import get_states_info





def hlmem_to_firmem(module):
    """Convert seq.hlmem operations to seq.firmem"""
    hlmem_ops = []
    
    def callback(op):
        hlmem_ops.append(op)
        return WalkResult.ADVANCE
    
    walk_with_filter(module.operation, ["seq.hlmem"], callback, WalkOrder.POST_ORDER)
    
    for op in hlmem_ops:
        numWords, wordType = str(op.result.type)[11:-1].split('x')
        bitWidth = hw.get_bitwidth(circt.ir.Type.parse(wordType))
        mem_type = circt.ir.Type.parse(f"!seq.firmem<{numWords} x {bitWidth}>")
        
        hlmem = op.opview
        clk = hlmem.clk
        rst = hlmem.rst
        name = hlmem.name
        
        with circt.ir.InsertionPoint(op):
            ruw = circt.ir.Attribute.parse("0 : i32")
            wuw = circt.ir.Attribute.parse("0 : i32")
            firmem = seq.firmem(mem_type, 1, 1, ruw, wuw, name=name)

        for use in op.result.uses:
            user_op = use.owner
            if user_op.name == "seq.read":
                with circt.ir.InsertionPoint(user_op):
                    address = user_op.addresses[0]
                    read_op = seq.firmem_read_port(firmem, address, clk, enable=user_op.rdEn)
                firmem.owner.opview.readLatency = circt.ir.Attribute.parse(f"{user_op.latency.value} : i32")
                user_op.result.replace_all_uses_with(read_op)
                user_op.erase()

            elif user_op.name == "seq.write":
                with circt.ir.InsertionPoint(user_op):
                    address = user_op.addresses[0]
                    write_op = seq.firmem_write_port(firmem, address, clk, user_op.inData, enable=user_op.wrEn)
                firmem.owner.opview.writeLatency = circt.ir.Attribute.parse(f"{user_op.latency.value} : i32")
                user_op.erase()
        
        op.erase()


def remove_verif_clocked_assert(module):
    """Remove verif.clocked_assert operations from the module"""
    verif_clocked_assert = []
    
    def callback(op):
        verif_clocked_assert.append(op)
        return WalkResult.ADVANCE
    
    walk_with_filter(module.operation, ["verif.clocked_assert"], callback, WalkOrder.POST_ORDER)
    
    for op in verif_clocked_assert:
        op.erase()


def translate_to_llvm(hw_module: circt.ir.Module):
    """
    Lower hardware module through Arc dialect to LLVM IR.
    Follows the official arcilator lowering pipeline.
    """
    def run_pass(m, ps):
        PassManager.parse(ps).run(m.operation)

    m = circt.ir.Module.parse(str(hw_module))

    # ESI lowering pipeline (lowers !esi.channel, esi.wrap/unwrap, esi.stage to HW)
    run_pass(m, "builtin.module(lower-esi-to-physical, lower-esi-ports, lower-esi-to-hw)")

    # Arc preprocessing
    run_pass(m, "builtin.module(hw.module(lower-seq-fifo))")
    remove_verif_clocked_assert(m)
    hlmem_to_firmem(m)
    run_pass(m, "builtin.module(lower-seq-firmem)")
    run_pass(m, "builtin.module(arc-add-taps)")
    run_pass(m, "builtin.module(arc-strip-sv)")
    run_pass(m, "builtin.module(arc-infer-memories)")
    run_pass(m, "builtin.module(arc-canonicalizer)")
    run_pass(m, "builtin.module(cse)")
    
    # Arc conversion
    run_pass(m, "builtin.module(convert-to-arcs)")
    run_pass(m, "builtin.module(arc-dedup)")
    run_pass(m, "builtin.module(hw-flatten-modules)")
    run_pass(m, "builtin.module(cse)")
    run_pass(m, "builtin.module(arc-canonicalizer)")

    # Arc optimization
    run_pass(m, "builtin.module(arc-split-loops)")
    run_pass(m, "builtin.module(arc-dedup)")
    run_pass(m, "builtin.module(arc-infer-state-properties)")
    run_pass(m, "builtin.module(cse)")
    run_pass(m, "builtin.module(arc-canonicalizer)")
    run_pass(m, "builtin.module(hw.module(arc-merge-taps))")
    run_pass(m, "builtin.module(arc-make-tables)")
    run_pass(m, "builtin.module(cse)")
    run_pass(m, "builtin.module(arc-canonicalizer)")

    # Arc state lowering
    run_pass(m, "builtin.module(arc-inline)")
    run_pass(m, "builtin.module(arc-lower-state)")
    run_pass(m, "builtin.module(arc-merge-ifs)")
    run_pass(m, "builtin.module(cse)")
    run_pass(m, "builtin.module(arc-canonicalizer)")

    # Arc state allocation
    run_pass(m, "builtin.module(arc-lower-arcs-to-funcs)")
    run_pass(m, "builtin.module(arc.model(arc-allocate-state))")
    states = get_states_info(m)
    run_pass(m, "builtin.module(arc-lower-clocks-to-funcs)")
    run_pass(m, "builtin.module(arc-split-funcs)")
    run_pass(m, "builtin.module(cse)")
    run_pass(m, "builtin.module(arc-canonicalizer)")

    # Final lowering to LLVM
    run_pass(m, "builtin.module(convert-comb-to-arith)")
    run_pass(m, "builtin.module(hw-convert-bitcasts)")
    run_pass(m, "builtin.module(lower-arc-to-llvm)")
    run_pass(m, "builtin.module(cse)")
    run_pass(m, "builtin.module(arc-canonicalizer)")

    return m, states
