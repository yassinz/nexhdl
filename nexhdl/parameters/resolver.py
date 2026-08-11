"""
Parameter Resolver - Unified parameter resolution
"""

from typing import Any, Dict
from .proxy import is_parameter

class ParameterResolver:
    """Unified parameter resolution - single recursive function."""
    
    @staticmethod
    def resolve(annotation: Any, param_dict: Dict[str, Any]) -> Any:
        """Recursively resolve annotations, substituting parameters."""
        # Parameter or Expression - evaluate it
        if is_parameter(annotation):
            return annotation.evaluate(param_dict)
        
        # Type implements resolution protocol
        if hasattr(annotation, '__resolve_parameters__'):
            return annotation.__resolve_parameters__(param_dict)
        
        # Generic type (typing.List[T], etc.)
        if hasattr(annotation, '__origin__'):
            args = getattr(annotation, '__args__', ())
            new_args = tuple(ParameterResolver.resolve(arg, param_dict) for arg in args)
            return annotation.__origin__[new_args] if new_args else annotation
        
        return annotation
    
    @staticmethod
    def resolve_annotations(annotations: Dict[str, Any], param_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve all annotations in a dictionary."""
        return {k: ParameterResolver.resolve(v, param_dict) for k, v in annotations.items()}
