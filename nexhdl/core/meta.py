"""
ModuleMeta - Metaclass for Module
"""

import types
from circt.dialects import hw

from .ports import PortDirection
from ..parameters import ParameterizedNamespace, ParameterResolver, Param, specialize_function
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
        
        interfaces = {}
        
        # If it's a parameterized module (already has _port_type_objs), just set the name and return
        if '_port_type_objs' in namespace:
            namespace['name'] = hw_name
            return super().__new__(cls, name, bases, namespace)
        
        from ..interfaces.base import InterfacePort, Interface, InterfaceRole
        
        for port_name, annotation in namespace.get('__annotations__', {}).items():
            # Check if annotation is an Interface or InterfacePort
            if isinstance(annotation, type) and issubclass(annotation, Interface):
                annotation = InterfacePort(annotation, role=InterfaceRole.OUTPUT)
            
            if isinstance(annotation, InterfacePort):
                interfaces[port_name] = annotation
                flattened = annotation.get_flattened_ports(port_name)
                for full_name, direction, type_obj in flattened:
                    if type_obj is None:
                        raise ValueError(f"Interface port '{full_name}' has no type specified.")
                    port_types[full_name] = type_obj
                    direction_map = {
                        hw.ModulePortDirection.INPUT: 'input',
                        hw.ModulePortDirection.OUTPUT: 'output',
                        hw.ModulePortDirection.INOUT: 'inout'
                    }
                    key = direction_map.get(direction)
                    if key:
                        ports[key].append((full_name, direction))
                continue

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
        namespace['_interfaces'] = interfaces
        
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
        extended_params = param_dict.copy()
        new_namespace = extended_params.copy()
        
        # Copy structural metadata
        for key in ('inputs', 'outputs', 'inouts', 'ports'):
            if hasattr(cls, key):
                new_namespace[key] = getattr(cls, key)
        
        # Resolve class attributes (constants, types, expressions)
        for key, value in cls.__dict__.items():
            if (key.startswith('_') and key != '__init__') or key in param_dict:
                continue
            if not isinstance(value, types.FunctionType):
                new_namespace[key] = ParameterResolver.resolve(value, extended_params)
                extended_params[key] = new_namespace[key]
        
        # Specialize methods with resolved parameters
        for key, value in cls.__dict__.items():
            if isinstance(value, types.FunctionType):
                new_namespace[key] = specialize_function(value, extended_params)
        
        # Resolve port types
        if hasattr(cls, '_port_type_objs'):
            resolved_ports = {}
            for name, type_obj in cls._port_type_objs.items():
                resolved = ParameterResolver.resolve(type_obj, extended_params)
                try:
                    resolved = to_nex_type(resolved)
                except TypeError:
                    pass
                resolved_ports[name] = resolved
            new_namespace['_port_type_objs'] = resolved_ports

        # Resolve interfaces
        if hasattr(cls, '_interfaces'):
            resolved_interfaces = {}
            for name, iface in cls._interfaces.items():
                resolved_interfaces[name] = ParameterResolver.resolve(iface, extended_params)
            new_namespace['_interfaces'] = resolved_interfaces
        
        # Resolve annotations
        if hasattr(cls, '__annotations__'):
            new_namespace['__annotations__'] = ParameterResolver.resolve_annotations(
                cls.__annotations__, extended_params
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
        
        # Expand interface handles in kwargs if any
        if kwargs and hasattr(cls, '_interfaces'):
            from ..interfaces.base import InterfaceHandle
            expanded_kwargs = {}
            for k, v in kwargs.items():
                if k in cls._interfaces and isinstance(v, InterfaceHandle):
                    iface_spec = cls._interfaces[k]
                    for port_name in getattr(iface_spec.interface_cls, '_port_defs', {}):
                        full_name = f"{k}_{port_name}"
                        expanded_kwargs[full_name] = getattr(v, port_name)
                else:
                    expanded_kwargs[k] = v
            kwargs = expanded_kwargs

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
        return specialize_function(func, param_dict)
