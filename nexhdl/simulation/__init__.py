"""
NexHDL Simulator - Following CIRCT Arcilator Pattern

This simulator implementation mirrors the official CIRCT arcilator C++ implementation:
- transforms.py: IR lowering pipeline (like arcilator passes)
- state.py: State extraction (like Layout classes) and Type-aware buffer read/write
- vcd.py: VCD tracing (like ValueChangeDump)
- simulation.py: Main simulator (like Module/View classes)
"""

from .simulator import Simulator
from .states import PortData, StateData, MemoryData, StatesInfo, get_states_info, read_value, write_value
from .transforms import translate_to_llvm
from .vcd import VCDTracer

__all__ = [
    'Simulator', 'PortData', 'StateData', 'MemoryData', 'StatesInfo', 'get_states_info', 
    'translate_to_llvm', 'VCDTracer',
    'read_value', 'write_value',
]


