"""
Parameterized Metaclass - For generic types
"""

from abc import ABCMeta
from typing import Any, Dict
import types

from .proxy import ParameterProxy
from .resolver import ParameterResolver


class Param:
    """
    Parameter validator for PEP 695 generics.
    
    Usage:
        PositiveInt = Param[int](lambda x: x > 0, "Must be positive")
        
        class Buffer[DEPTH: PositiveInt](Module):
            ...
    """
    def __init__(self, base_type, predicate, error_msg):
        self.base_type = base_type
        self.predicate = predicate
        self.error_msg = error_msg

    def validate(self, name, value):
        if isinstance(value, ParameterProxy):
            return 

        if not isinstance(value, self.base_type):
            raise TypeError(
                f"Parameter '{name}' must be {self.base_type.__name__}, "
                f"got {type(value).__name__}"
            )

        if not self.predicate(value):
            raise ValueError(
                f"Validation failed for parameter '{name}': "
                f"{self.error_msg} (value: {value})"
            )

    @classmethod
    def __class_getitem__(cls, base_type):
        def factory(predicate, error_msg):
            return cls(base_type, predicate, error_msg)
        return factory


class ParameterizedNamespace(dict):
    """
    Custom namespace that intercepts type parameter injection.
    
    When Python processes a generic class like `class Foo[T, N](Base)`,
    it sets __type_params__ in the namespace. We intercept this and
    inject ParameterProxy objects for each parameter.
    """
    
    def __setitem__(self, key, value):
        if key == '__type_params__':
            for param in value:
                # Inject proxy for each type parameter
                name = param.__name__
                self[name] = ParameterProxy(name)
        
        super().__setitem__(key, value)


class ParameterizedMeta(ABCMeta):
    """
    Metaclass for parameterized types (Struct, Union, etc.).
    
    Handles:
    - Parameter injection via __getitem__: MyType[T, N]
    - Parameter resolution via __resolve_parameters__ protocol
    - Namespace preparation for type parameters
    """
    
    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        return ParameterizedNamespace()
    
    def __getitem__(cls, params):
        """Parameterization: MyType[T, N]"""
        
        if not isinstance(params, tuple):
            params = (params,)
        
        if not hasattr(cls, '__type_params__'):
            raise TypeError(f"{cls.__name__} is not a parameterized type")
        
        type_params = cls.__type_params__
        
        if len(params) != len(type_params):
            raise TypeError(
                f"{cls.__name__} expects {len(type_params)} parameters, "
                f"got {len(params)}"
            )
        
        # Validate parameters against bounds
        for tp, val in zip(type_params, params):
            bound = getattr(tp, "__bound__", None)
            if isinstance(bound, Param):
                bound.validate(tp.__name__, val)
        
        # Map parameter names to values
        param_dict = {p.__name__: v for p, v in zip(type_params, params)}
        
        # Resolve annotations
        new_annotations = {}
        if hasattr(cls, '__annotations__'):
            new_annotations = ParameterResolver.resolve_annotations(
                cls.__annotations__, param_dict
            )
        
        # Create resolved class namespace
        class_name = f'{cls.__name__}[{", ".join(str(p) for p in params)}]'
        new_namespace = {
            '__annotations__': new_annotations,
            '__module__': cls.__module__,
            '__qualname__': class_name,
            '_generic_base': cls,
            '_type_args': params,
            **param_dict,
        }
        
        # Copy methods from original class
        for key, value in cls.__dict__.items():
            if key in new_namespace:
                continue
            if key in ('__dict__', '__weakref__', '__annotations__', 
                      '_cached_type', '_hw_type', '__type_params__'):
                continue
            
            # For methods, inject parameters into their globals
            if isinstance(value, types.FunctionType):
                new_globals = value.__globals__.copy()
                new_globals.update(param_dict)
                
                # Handle closure variables
                new_closure = value.__closure__
                if value.__code__.co_freevars and value.__closure__:
                    freevars = value.__code__.co_freevars
                    closure_cells = list(value.__closure__)
                    
                    for i, freevar in enumerate(freevars):
                        if freevar in param_dict:
                            def make_cell(val):
                                return (lambda: val).__closure__[0]
                            closure_cells[i] = make_cell(param_dict[freevar])
                    
                    new_closure = tuple(closure_cells)
                
                new_func = types.FunctionType(
                    value.__code__,
                    new_globals,
                    value.__name__,
                    value.__defaults__,
                    new_closure
                )
                new_namespace[key] = new_func
            else:
                new_namespace[key] = value
        
        # Create new class using the SAME metaclass
        return type(cls)(class_name, (cls,), new_namespace)
    
    def __resolve_parameters__(cls, param_dict: Dict[str, Any]):
        """Protocol method for parameter resolution."""
        if not hasattr(cls, '__annotations__'):
            return cls
        
        new_annotations = ParameterResolver.resolve_annotations(cls.__annotations__, param_dict)
        if new_annotations == cls.__annotations__:
            return cls
        
        # Create new class with resolved annotations
        new_namespace = {k: v for k, v in cls.__dict__.items()
                        if k not in ('__dict__', '__weakref__', '__annotations__', 
                                    '_cached_type', '_hw_type')}
        new_namespace['__annotations__'] = new_annotations
        
        return type(cls)(cls.__name__, cls.__bases__, new_namespace)

    def __repr__(cls):
        return cls.__name__
