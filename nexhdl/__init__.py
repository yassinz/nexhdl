"""
NexHDL - A clean, composable HDL type system
"""

__version__ = "0.1.0"

# Initialize CIRCT context management
import circt
import atexit

# Single global context - entered on module load
GlobalContext = circt.ir.Context()
GlobalContext.__enter__()
GlobalContext.allow_unregistered_dialects = True
circt.register_dialects(GlobalContext)
atexit.register(GlobalContext.__exit__, None, None, None)

GlobalLocation = circt.ir.Location.unknown(GlobalContext)
GlobalLocation.__enter__()
atexit.register(GlobalLocation.__exit__, None, None, None)


def get_context():
    """Get the global CIRCT context."""
    return GlobalContext


def get_location():
    """Get the global CIRCT location."""
    return GlobalLocation


# Public API
from .types import (
    NexType, NexValue,
    Logic, LogicType,
    Array, ArrayType,
    Struct, StructType,
    Union, UnionType,
    Clock, ClockType, Reset, ResetType,
    to_nex_type, get_value_class, wrap,
)

from .core import Module, INPUT, OUTPUT, INOUT

from .primitives import Reg, Wire, Mux, Map, Mem, Fifo

from .parameters import ParameterProxy, ParameterResolver, clog2, Param

from .simulation import Simulator



__all__ = [
    # CIRCT
    'get_context', 'get_location',

    # Base
    'NexType', 'NexValue',
    
    # Types
    'Logic', 'LogicType',
    'Array', 'ArrayType', 
    'Struct', 'StructType',
    'Union', 'UnionType',
    'Clock', 'ClockType',
    'Reset', 'ResetType',
    
    # Module
    'Module', 'INPUT', 'OUTPUT', 'INOUT',
    
    # Primitives
    'Reg', 'Wire', 'Mux', 'Map', 'Mem', 'Fifo',
    
    # Utilities
    'wrap', 'to_nex_type', 'get_value_class', 'clog2',
    
    # Parameters
    'ParameterProxy', 'ParameterResolver', 'Param',

    # Simulators
    'Simulator',
]
