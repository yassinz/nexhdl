"""
Union Type and Value

Stores union data as a flattened bit vector (Logic[max_width]).
Uses bit manipulation and casts to handle fields.
"""

from circt.dialects import hw
import circt
from typing import Dict, Any

from .base import NexType, NexValue, to_nex_type
from ..parameters import ParameterizedMeta, ParameterResolver
from .logic import Logic, LogicType


class UnionType(NexType):
    """
    NexType implementation for Union.
    
    A Union is represented in hardware as a flat bit vector of size max(fields).
    """
    
    def __init__(self, union_class):
        self._union_class = union_class
        self._fields = None
        self._hw_type = None
        self._max_width = 0
    
    def _build_type(self):
        if self._fields is not None:
            return
        
        annotations = getattr(self._union_class, '__annotations__', {})
        if not annotations:
            raise TypeError(
                f"Union class {self._union_class.__name__} has no field annotations"
            )
        
        self._fields = {}
        max_width = 0
        
        for name, field_type in annotations.items():
            circt_type = NexType.to_circt(field_type)
            width = hw.get_bitwidth(circt_type)
            self._fields[name] = (circt_type, width)
            max_width = max(max_width, width)
        
        self._max_width = max_width
        self._hw_type = LogicType(max_width).type
    
    @property
    def type(self) -> circt.ir.Type:
        self._build_type()
        return self._hw_type
    
    @property
    def fields(self):
        self._build_type()
        return self._fields
        
    @property
    def max_width(self):
        self._build_type()
        return self._max_width
    
    @property
    def union_class(self):
        return self._union_class
    
    def __call__(self, value=None, **kwargs) -> 'Union':
        return self._union_class(value, **kwargs)
    
    def __repr__(self):
        # For dynamic unions, show field names
        if self._union_class.__name__.startswith('Union_'):
            annotations = getattr(self._union_class, '__annotations__', {})
            if annotations:
                fields = ', '.join(f"{k}: {v}" for k, v in annotations.items())
                return f"<{self._union_class.__name__}<{{{fields}}}>"
        return f"<{self._union_class.__name__}>"

    def __resolve_parameters__(self, param_dict):
        union_class = self._union_class
        if hasattr(union_class, '__resolve_parameters__'):
            resolved_class = union_class.__resolve_parameters__(param_dict)
            if resolved_class is not union_class:
                return UnionType(resolved_class)
        return self


class UnionMeta(ParameterizedMeta):
    """
    Metaclass for Union that makes classes behave like types.
    """
    
    def __new__(mcs, name, bases, namespace):
        namespace['_cached_type'] = None
        namespace['_hw_type'] = None
        return super().__new__(mcs, name, bases, namespace)
    
    @property
    def type(cls) -> circt.ir.Type:
        return cls.get_hw_type()
    
    @property
    def _nex_type(cls) -> UnionType:
        if cls._cached_type is None:
            cls._cached_type = UnionType(cls)
        return cls._cached_type


class Union(NexValue, metaclass=UnionMeta):
    """
    Base class for hardware unions (implemented as bag of bits).
    """
    
    @classmethod
    def __resolve_parameters__(cls, param_dict):

        if hasattr(cls, '_generic_base') and hasattr(cls, '_type_args'):
            generic_base = cls._generic_base
            type_args = cls._type_args
            new_args = []
            changed = False
            for arg in type_args:
                resolved = ParameterResolver.resolve(arg, param_dict)
                new_args.append(resolved)
                if resolved != arg:
                    changed = True
            
            if changed:
                if len(new_args) == 1:
                    return generic_base[new_args[0]]
                else:
                    return generic_base[tuple(new_args)]

        elif hasattr(cls, '__type_params__') and cls.__type_params__:
            type_params = cls.__type_params__
            param_values = []
            for tp in type_params:
                name = tp.__name__
                if name in param_dict:
                    param_values.append(param_dict[name])
                else:
                    return cls
            
            if param_values:
                if len(param_values) == 1:
                    return cls[param_values[0]]
                else:
                    return cls[tuple(param_values)]
        
        return cls
    
    def __init__(self, value=None, **kwargs):
        # Check if this is a generic class without parameters
        if hasattr(self.__class__, '__type_params__') and self.__class__.__type_params__:
            raise TypeError(
                f"Cannot instantiate generic type {self.__class__.__name__} without parameters. "
                f"Use {self.__class__.__name__}[...] with concrete type parameters."
            )
        
        if isinstance(value, (circt.ir.Value, NexValue)):
            self._init_from_ir(value)
        elif value is None and not kwargs:
            self._init_zero()
        elif kwargs:
            self._init_from_field(kwargs)
        else:
            raise TypeError(
                f"Cannot create {type(self).__name__} from {type(value)}. "
                f"Use keyword arguments or a CIRCT value."
            )
    
    def _init_from_ir(self, ir_value):
        self._value = self.type_like()._maybe_cast(ir_value)
    
    def _init_zero(self):
        # Create zero of max width
        width = self.type_like().max_width
        self._value = Logic[width](0).value
    
    def _init_from_field(self, field_dict: Dict[str, Any]):
        if len(field_dict) != 1:
            raise ValueError("Union construction requires exactly one field")
        
        field_name, field_value = list(field_dict.items())[0]
        annotations = self.__annotations__
        
        if field_name not in annotations:
             raise ValueError(f"Unknown field '{field_name}'")
        
        # Get field type info
        target_nex_type = to_nex_type(annotations[field_name])
        
        # Convert input value to correct type first (e.g. handle ints)
        if isinstance(field_value, int):
             if isinstance(target_nex_type, LogicType):
                 if (field_value + (field_value < 0)).bit_length() > target_nex_type.bit_width:
                     raise ValueError(
                         f"Integer {field_value} out of range for union field '{field_name}' "
                         f"({target_nex_type})"
                     )
             typed_val = target_nex_type(field_value)
        elif isinstance(field_value, NexValue):
             if field_value.type != target_nex_type.type:
                 raise TypeError(
                     f"Type mismatch for union field '{field_name}': "
                     f"expected {target_nex_type}, got {field_value.type_like()}"
                 )
             typed_val = field_value
        else:
             raise TypeError(f"Invalid value type: {type(field_value)}")
             
        # Extract IR value
        val_ir = typed_val.value
        val_width = hw.get_bitwidth(val_ir.type)
        max_width = self.type_like().max_width
        
        # 1. Ensure it is Logic (int) so we can zext
        # LogicType(val_width)(val_ir) will cast if val_ir is not Int
        val_logic = LogicType(val_width)(val_ir)
            
        # 2. Zero extend to max_width
        final_logic = val_logic.zext(max_width)
        
        self._value = final_logic.value
        
    @classmethod
    def get_hw_type(cls) -> circt.ir.Type:
        return cls._nex_type.type
        
    @property
    def value(self) -> circt.ir.Value:
        return self._value
    
    def type_like(self) -> UnionType:
        return self.__class__._nex_type
    
    def __getattr__(self, name: str):
        if name.startswith('_') or name in ('value', 'type'):
             raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
             
        annotations = getattr(self.__class__, '__annotations__', {})
        if name not in annotations:
             raise AttributeError(f"'{type(self).__name__}' has no field '{name}'")
        
        # Get field type
        field_type_annotation = annotations[name]
        nex_type = to_nex_type(field_type_annotation)
        
        # Get field width
        u_type = self.type_like()
        _, field_width = u_type.fields[name]
        
        # Extract bits and cast to proper type
        storage_logic = Logic(self._value)
        truncated = storage_logic.trunc(field_width)
        
        # Cast truncated bits to the field's actual type
        return nex_type(truncated)

    def __repr__(self):
        return f"<{type(self).__name__}>"


class DynamicUnion(UnionType):
     pass
