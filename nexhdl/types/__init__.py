"""
Data Types

User-facing hardware types: Logic, Array, Struct, Union, Clock
"""

from .base import NexType, NexValue, to_nex_type, get_value_class, wrap
from .logic import Logic, LogicType
from .array import Array, ArrayType
from .struct import Struct, StructType
from .union import Union, UnionType
from .clock import Clock, ClockType, Reset, ResetType

__all__ = [
    'NexType', 'NexValue', 'to_nex_type', 'get_value_class', 'wrap',
    'Logic', 'LogicType',
    'Array', 'ArrayType',
    'Struct', 'StructType',
    'Union', 'UnionType',
    'Clock', 'ClockType',
    'Reset', 'ResetType',
]
