"""
Compilation context manager for nested module compilation.
"""

import threading

_context_stack = threading.local()


class CompilationContext:
    """Thread-safe global compilation context."""
    def __init__(self):
        self.model = None
        self.instances = {}


class ScopeContext:
    """
    Module-local scope for tracking primitives.
    Wraps the global CompilationContext.
    """
    def __init__(self, global_context):
        self.global_context = global_context
        self.regs = []
        self.wires = []
    
    def add_reg(self, reg):
        self.regs.append(reg)
        
    def add_wire(self, wire):
        self.wires.append(wire)
    
    def __getattr__(self, name):
        """Proxy attributes to global context."""
        return getattr(self.global_context, name)
    
    def __setattr__(self, name, value):
        """Proxy attribute setting to global context."""
        if name in ('global_context', 'regs', 'wires'):
            object.__setattr__(self, name, value)
        else:
            setattr(self.global_context, name, value)


class CompilationContextManager:
    """Context manager to track current compilation context."""
    
    def __init__(self, context):
        self.context = context
    
    def __enter__(self):
        if not hasattr(_context_stack, 'stack'):
            _context_stack.stack = []
        _context_stack.stack.append(self.context)
        return self.context
    
    def __exit__(self, *args):
        _context_stack.stack.pop()


def get_current_context():
    """Get the current compilation context, if any."""
    if not hasattr(_context_stack, 'stack') or not _context_stack.stack:
        return None
    return _context_stack.stack[-1]
