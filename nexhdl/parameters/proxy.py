"""
Simplified Parameter System
"""

import operator
from typing import Any, Dict


class ParameterProxy:
    """Placeholder for unresolved type parameters and expressions."""
    
    OPS = {
        'mul': operator.mul,
        'add': operator.add,
        'sub': operator.sub,
        'floordiv': operator.floordiv,
        'pow': operator.pow,
        'and': operator.and_,
        'or': operator.or_,
        'xor': operator.xor,
        'lshift': operator.lshift,
        'rshift': operator.rshift,
        'invert': operator.invert,
        'clog2': lambda x: (x - 1).bit_length() if x > 0 else 0,
    }
    
    def __init__(self, name: str = None, op: str = None, args: list = None):
        self.name = name
        self.op = op
        self.args = args or []
    
    def evaluate(self, param_dict: Dict[str, Any]) -> Any:
        if self.name is not None:
            return param_dict.get(self.name, self)
        
        if self.op is not None:
            resolved_args = [
                arg.evaluate(param_dict) if isinstance(arg, ParameterProxy) else arg
                for arg in self.args
            ]
            
            # If any argument is still a parameter, return a new expression proxy
            if any(isinstance(a, ParameterProxy) for a in resolved_args):
                return ParameterProxy(op=self.op, args=resolved_args)
            
            return self.OPS[self.op](*resolved_args)
        
        return self
    
    def _op(self, op_name: str, *others) -> 'ParameterProxy':
        """Create a new expression proxy."""
        return ParameterProxy(op=op_name, args=[self, *others])
    
    # Arithmetic - return new proxies
    def __mul__(self, other): return self._op('mul', other)
    def __rmul__(self, other): return ParameterProxy(op='mul', args=[other, self])
    def __add__(self, other): return self._op('add', other)
    def __radd__(self, other): return ParameterProxy(op='add', args=[other, self])
    def __sub__(self, other): return self._op('sub', other)
    def __rsub__(self, other): return ParameterProxy(op='sub', args=[other, self])
    def __floordiv__(self, other): return self._op('floordiv', other)
    def __rfloordiv__(self, other): return ParameterProxy(op='floordiv', args=[other, self])
    def __pow__(self, other): return self._op('pow', other)
    def __rpow__(self, other): return ParameterProxy(op='pow', args=[other, self])
    
    # Bitwise
    def __and__(self, other): return self._op('and', other)
    def __rand__(self, other): return ParameterProxy(op='and', args=[other, self])
    def __or__(self, other): return self._op('or', other)
    def __ror__(self, other): return ParameterProxy(op='or', args=[other, self])
    def __xor__(self, other): return self._op('xor', other)
    def __rxor__(self, other): return ParameterProxy(op='xor', args=[other, self])
    def __lshift__(self, other): return self._op('lshift', other)
    def __rlshift__(self, other): return ParameterProxy(op='lshift', args=[other, self])
    def __rshift__(self, other): return self._op('rshift', other)
    def __rrshift__(self, other): return ParameterProxy(op='rshift', args=[other, self])
    def __invert__(self): return self._op('invert')
    
    def __repr__(self):
        if self.name:
            return f"Param({self.name})"
        return f"{self.op}({', '.join(map(str, self.args))})"


def clog2(x):
    """Calculate ceil(log2(x))."""
    if isinstance(x, int):
        return (x - 1).bit_length() if x > 0 else 0
    if isinstance(x, ParameterProxy):
        return x._op('clog2')
    # Fallback/Default case (e.g. if x is already some other expression)
    return ParameterProxy(op='clog2', args=[x])


def is_parameter(obj):
    """Check if object is a parameter or expression (all unified in ParameterProxy)."""
    return isinstance(obj, ParameterProxy) or type(obj).__name__ == 'ParameterProxy'
