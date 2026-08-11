"""
TraceVars - Automatic name hinting
"""

import sys
from ..types.base import NexValue


class TraceVars:
    """
    Context manager that sets names on NexValue objects
    based on their variable names in the calling scope.
    """
    
    def __init__(self):
        self.target_frame = None
        self.local_vars = {}
        self.old_trace = None
    
    def _trace(self, frame, event, arg):
        if self.old_trace is not None:
            self.old_trace(frame, event, arg)
        
        if self.target_frame is None and event == 'call':
            self.target_frame = frame
            return self._trace
        
        if event == 'return' and frame is self.target_frame:
            self.local_vars = frame.f_locals.copy()
            return self.old_trace
        
        return self._trace
    
    def _update_names(self):
        for name, value in self.local_vars.items():
            if isinstance(value, NexValue):
                value.set_name(name)
    
    def __enter__(self):
        self.old_trace = sys.gettrace()
        sys.settrace(self._trace)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        sys.settrace(self.old_trace)
        self._update_names()
        self.target_frame = None
        self.local_vars = {}
