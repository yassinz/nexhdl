"""
Module System

Modules are the top-level hardware units with ports.
"""

from .ports import INPUT, OUTPUT
from .module import Module
from .io import IO

__all__ = ['Module', 'INPUT', 'OUTPUT', 'IO']
