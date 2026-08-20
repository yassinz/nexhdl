"""
ModuleMeta - Metaclass for Module
"""

import types
from circt.dialects import hw

from .ports import PortDirection
from ..parameters import ParameterizedNamespace, ParameterResolver, Param
from ..types.base import to_nex_type


class ModuleMeta(type):
    """Metaclass that processes module port annotations and parameters."""
    
    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        return ParameterizedNamespace()
    
    def __new__(cls, name, bases, namespace):
        ports = {'input': [], 'output': [], 'inout': []}
        port_types = {}
        hw_name = name.replace('[', '_').replace(']', '').replace(',', 'x').replace(' ', '')
        hw_name = hw_name.replace('<', '').replace('>', '')
        
        # If it's a parameterized module (already has _port_type_objs), just set the name and return
        if '_port_type_objs' in namespace:
            namespace['name'] = hw_name
            return super().__new__(cls, name, bases, namespace)
        
        for port_name, annotation in namespace.get('__annotations__', {}).items():
            if not isinstance(annotation, PortDirection):
                continue
            
            if annotation.type_obj is None:
                raise ValueError(
                    f"Port '{port_name}' must have an explicit type. "
                    f"Use {annotation.__class__.__name__}[Type] syntax."
                )
            
            port_types[port_name] = annotation.type_obj
            
            # Map direction to port list
            direction_map = {
                hw.ModulePortDirection.INPUT: 'input',
                hw.ModulePortDirection.OUTPUT: 'output',
                hw.ModulePortDirection.INOUT: 'inout'
            }
            key = direction_map.get(annotation.direction)
            if key:
                ports[key].append((port_name, annotation.direction))
        
        namespace['name'] = hw_name
        namespace['inputs'] = ports['input']
        namespace['outputs'] = ports['output']
        namespace['inouts'] = ports['inout']
        namespace['ports'] = ports['input'] + ports['output'] + ports['inout']
        namespace['_port_type_objs'] = port_types
        
        return super().__new__(cls, name, bases, namespace)
    
    def __getitem__(cls, params):
        """Parameterization: MyModule[T, N]"""
        if not isinstance(params, tuple):
            params = (params,)
        
        type_params = getattr(cls, '__type_params__', ())
        if not type_params:
            raise TypeError(f"Module '{cls.__name__}' is not parameterized.")
        
        if len(params) != len(type_params):
            raise TypeError(
                f"Module '{cls.__name__}' expects {len(type_params)} type parameters, "
                f"but got {len(params)}."
            )
        
        # Validate parameters against bounds
        for tp, val in zip(type_params, params):
            bound = getattr(tp, "__bound__", None)
            if isinstance(bound, Param):
                bound.validate(tp.__name__, val)
        
        param_dict = {p.__name__: v for p, v in zip(type_params, params)}
        new_namespace = cls._build_parameterized_namespace(param_dict)
        class_name = f'{cls.__name__}[{",".join(map(str, params))}]'
        
        return type(class_name, (cls,), new_namespace)

    
    def _build_parameterized_namespace(cls, param_dict):
        """Build namespace for parameterized class."""
        new_namespace = param_dict.copy()
        
        # Resolve port types first (special case)
        if hasattr(cls, '_port_type_objs'):
            resolved_ports = {}
            for name, type_obj in cls._port_type_objs.items():
                resolved = ParameterResolver.resolve(type_obj, param_dict)
                # Normalize resolved type (e.g. int -> Logic)
                try:
                    resolved = to_nex_type(resolved)
                except TypeError:
                    pass
                resolved_ports[name] = resolved
            new_namespace['_port_type_objs'] = resolved_ports
        
        # Copy other class attributes (except 'name', handle that separately)
        for key in ('inputs', 'outputs', 'inouts', 'ports'):
            if hasattr(cls, key):
                new_namespace[key] = getattr(cls, key)
        
        for key, value in cls.__dict__.items():
            if key.startswith('_') and key != '__init__' or key in param_dict:
                continue
            
            if isinstance(value, types.FunctionType):
                new_namespace[key] = cls._inject_params_to_func(value, param_dict)
            else:
                new_namespace[key] = value
        
        # Resolve annotations
        if hasattr(cls, '__annotations__'):
            new_namespace['__annotations__'] = ParameterResolver.resolve_annotations(
                cls.__annotations__, param_dict
            )
        
        return new_namespace
    
    def __call__(cls, **kwargs):
        """Handle module instantiation with parameter validation."""
        from .context import get_current_context
        
        # Check for unresolved type parameters
        if hasattr(cls, '__type_params__') and cls.__type_params__:
            param_names = [p.__name__ for p in cls.__type_params__]
            raise TypeError(
                f"Cannot instantiate parameterized module {cls.__name__} without type parameters.\n"
                f"Use {cls.__name__}[{', '.join(param_names)}](...) syntax."
            )
        
        # Validate port values if provided
        if kwargs and hasattr(cls, '_port_type_objs'):
            for port_name in kwargs:
                if port_name not in cls._port_type_objs:
                    available = list(cls._port_type_objs.keys())
                    raise ValueError(
                        f"Unknown port '{port_name}' for module {cls.__name__}. "
                        f"Available ports: {available}"
                    )
        
        # If port values provided, create instance handle
        if kwargs:
            temp = super().__call__()
            context = get_current_context()
            temp.compile(context)
            return temp.hw_module.instance(**kwargs)
        
        return super().__call__(**kwargs)
    
    @staticmethod
    def _inject_params_to_func(func, param_dict):
        """Inject parameters into function globals and closures."""
        new_globals = func.__globals__.copy()
        new_globals.update(param_dict)
        
        new_closure = func.__closure__
        if func.__code__.co_freevars and func.__closure__:
            closure_cells = list(func.__closure__)
            for i, freevar in enumerate(func.__code__.co_freevars):
                if freevar in param_dict:
                    closure_cells[i] = types.CellType(param_dict[freevar])
            new_closure = tuple(closure_cells)
        
        return types.FunctionType(
            func.__code__, new_globals, func.__name__, func.__defaults__, new_closure
        )
