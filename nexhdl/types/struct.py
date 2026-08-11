"""
Struct Type and Value

Structs are composite types with named fields.
- Define with class syntax
- Fields can be any NexType
- Supports parameterization with type variables
- Struct classes ARE types (via metaclass)

Usage:
    # Define a struct
    class Point(Struct):
        x: Logic[32]
        y: Logic[32]
    
    # Parameterized struct
    class Point[WIDTH](Struct):
        x: Logic[WIDTH]
        y: Logic[WIDTH]
        
        def __add__(self, other):
            return self.__class__(x=self.x + other.x, y=self.y + other.y)
    
    # Use as type (struct classes ARE types)
    Array[4, Point]              # Works because Point has .type property
    Array[4, Point[32]]          # Parameterized version
    
    # Create values
    p = Point(x=Logic[32](10), y=Logic[32](20))
    p = Point(ir_value)          # Wrap existing
    p = Point()                  # Zero-init
    
    # Access fields
    p.x, p.y                     # Returns wrapped values
"""

from circt.dialects import hw
import circt
from typing import Dict, Any

from .base import NexType, NexValue, to_nex_type
from .logic import LogicType

from ..parameters import ParameterizedMeta, ParameterResolver


class StructType(NexType):
    """
    Type class for Struct types.
    
    StructType is the NexType representation. Struct classes use StructMeta
    which exposes the same interface, so classes themselves can be used as types.
    """
    
    def __init__(self, struct_class):
        """
        Initialize from a Struct class.
        
        Args:
            struct_class: The Struct subclass defining the fields
        """
        self._struct_class = struct_class
        self._fields = None  # Lazy build
        self._hw_type = None
    
    def _build_type(self):
        """Build the CIRCT StructType from class annotations."""        
        if self._fields is not None:
            return
        
        annotations = getattr(self._struct_class, '__annotations__', {})
        if not annotations:
            raise TypeError(
                f"Struct class {self._struct_class.__name__} has no field annotations"
            )
        
        self._fields = []
        for name, field_type in annotations.items():
            circt_type = NexType.to_circt(field_type)
            self._fields.append((name, circt_type))
        
        self._hw_type = hw.StructType.get(self._fields)
    
    @property
    def type(self) -> circt.ir.Type:
        """Get the CIRCT StructType."""
        self._build_type()
        return self._hw_type
    
    @property
    def fields(self):
        """Get field info: [(name, circt_type), ...]"""
        self._build_type()
        return self._fields
    
    @property
    def struct_class(self):
        """The underlying Struct class."""
        return self._struct_class
    
    def __call__(self, value=None, **kwargs) -> 'Struct':
        """
        Create a Struct instance.
        
        Args:
            value: circt.ir.Value to wrap, or None
            **kwargs: Field values for construction
        
        Returns:
            Struct instance
        """
        return self._struct_class(value, **kwargs)
    
    def __resolve_parameters__(self, param_dict):
        """Resolve parameters in StructType."""
                
        resolved_class = ParameterResolver.resolve(self._struct_class, param_dict)
        return StructType(resolved_class) if resolved_class is not self._struct_class else self
    
    def __repr__(self):
        # For dynamic structs, show field names
        if self._struct_class.__name__.startswith('Struct_'):
            annotations = getattr(self._struct_class, '__annotations__', {})
            if annotations:
                fields = ', '.join(f"{k}: {v}" for k, v in annotations.items())
                return f"<{self._struct_class.__name__}<{{{fields}}}>"
        return f"<{self._struct_class.__name__}>"


class StructMeta(ParameterizedMeta):
    """
    Metaclass for Struct that makes classes behave like types.
    
    Key features:
    - .type property: Struct classes have .type returning hw.StructType
    - Parameterization: Struct[T, N] creates resolved subclass
    - Classes are callable to create instances
    """
    
    def __new__(mcs, name, bases, namespace):
        """Create the Struct class."""
        # Clear cached type on class creation
        namespace['_cached_type'] = None
        namespace['_hw_type'] = None
        return super().__new__(mcs, name, bases, namespace)
    
    @property
    def type(cls) -> circt.ir.Type:
        """
        Struct classes have .type property.
        """
        return cls.get_hw_type()
    
    @property
    def _nex_type(cls) -> StructType:
        """Get the StructType for this class."""
        if cls._cached_type is None:
            cls._cached_type = StructType(cls)
        return cls._cached_type



class Struct(NexValue, metaclass=StructMeta):
    """
    Base class for hardware struct types.
    
    Define structs by subclassing and adding annotated fields:
    
        class Point(Struct):
            x: Logic[32]
            y: Logic[32]
    
    Parameterized:
    
        class Point[WIDTH](Struct):
            x: Logic[WIDTH]
            y: Logic[WIDTH]
            
            def __add__(self, other):
                return self.__class__(x=self.x + other.x, y=self.y + other.y)
    """
    
    @classmethod
    def __resolve_parameters__(cls, param_dict):
        """Resolve parameters in this Struct class."""        
        # Already resolved via __getitem__
        if hasattr(cls, '_generic_base') and hasattr(cls, '_type_args'):
            new_args = [ParameterResolver.resolve(arg, param_dict) for arg in cls._type_args]
            if new_args != list(cls._type_args):
                result = cls._generic_base[tuple(new_args)] if len(new_args) > 1 else cls._generic_base[new_args[0]]
                return result
        
        # Unresolved generic - resolve via __getitem__
        if hasattr(cls, '__type_params__') and cls.__type_params__:
            param_values = [param_dict.get(tp.__name__) for tp in cls.__type_params__]
            if all(v is not None for v in param_values):
                return cls[tuple(param_values)] if len(param_values) > 1 else cls[param_values[0]]
        
        return cls
    
    def __init__(self, value=None, **kwargs):
        """
        Initialize a struct.
        
        Args:
            value: circt.ir.Value or NexValue to wrap, or None
            **kwargs: Field values for construction
        """
        # Check if this is a generic class without parameters
        if hasattr(self.__class__, '__type_params__') and self.__class__.__type_params__:
            raise TypeError(
                f"Cannot instantiate generic type {self.__class__.__name__} without parameters. "
                f"Use {self.__class__.__name__}[...] with concrete type parameters."
            )
        
        if isinstance(value, (circt.ir.Value, NexValue)):
            self._init_from_ir(value)
        elif (value is None or (isinstance(value, int) and value == 0)) and not kwargs:
            self._init_zero()
        elif kwargs:
            self._init_from_fields(kwargs)
        else:
            raise TypeError(
                f"Cannot create {type(self).__name__} from {type(value)}. "
                f"Use keyword arguments or a CIRCT value."
            )
    
    def _init_from_ir(self, ir_value):
        """Initialize by wrapping a CIRCT value or NexValue."""
        self._value = self.type_like()._maybe_cast(ir_value)
    
    def _init_zero(self):
        """Initialize with zero values for all fields."""        
        values = []
        for name, field_type in self.__annotations__.items():
            nex_type = to_nex_type(field_type)
            values.append(nex_type.zero().value)
        
        self._value = hw.struct_create(self.get_hw_type(), values)
    
    def _init_from_fields(self, field_dict: Dict[str, Any]):
        """Initialize from field values."""        
        annotations = self.__annotations__
        
        # Check for missing/extra fields
        missing = set(annotations.keys()) - set(field_dict.keys())
        extra = set(field_dict.keys()) - set(annotations.keys())
        
        if missing:
            raise ValueError(f"Missing fields: {missing}")
        if extra:
            raise ValueError(f"Unknown fields: {extra}")
        
        values = []
        for name, field_type in annotations.items():
            field_value = field_dict[name]
            target_type = to_nex_type(field_type)
            
            if isinstance(field_value, NexValue):
                if field_value.type != target_type.type:
                    raise TypeError(
                        f"Type mismatch for field '{name}': "
                        f"expected {target_type}, got {field_value.type_like()}"
                    )
                values.append(field_value.value)
            elif isinstance(field_value, int):
                from .logic import LogicType
                if isinstance(target_type, LogicType):
                    if (field_value + (field_value < 0)).bit_length() > target_type.bit_width:
                        raise ValueError(
                            f"Integer {field_value} out of range for field '{name}' "
                            f"({target_type})"
                        )
                values.append(target_type(field_value).value)
            else:
                raise TypeError(f"Invalid value for field '{name}': {type(field_value)}")
        
        self._value = hw.struct_create(self.get_hw_type(), values)
    
    @classmethod
    def get_hw_type(cls) -> circt.ir.Type:
        """Get the CIRCT hw.StructType."""
        if cls._hw_type is None:
            fields = []
            for name, field_type in cls.__annotations__.items():
                fields.append((name, NexType.to_circt(field_type)))
            cls._hw_type = hw.StructType.get(fields)
        
        return cls._hw_type
    
    @property
    def value(self) -> circt.ir.Value:
        """The underlying CIRCT value."""
        return self._value
    
    def type_like(self) -> StructType:
        """Return the StructType for this instance."""
        return self.__class__._nex_type
    
    def __getattr__(self, name: str):
        """
        Access struct fields by name.
        
        Returns the field wrapped in the appropriate type.
        """
        # Avoid recursion for internal attributes
        if name.startswith('_') or name in ('value', 'type'):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
        
        annotations = getattr(self.__class__, '__annotations__', {})
        
        if name not in annotations:
            raise AttributeError(f"'{type(self).__name__}' has no field '{name}'")
        
        field_names = list(annotations.keys())
        field_index = field_names.index(name)
        field_type = annotations[name]
        
        result_circt_type = NexType.to_circt(field_type)
        ir_value = hw.struct_extract(result_circt_type, self._value, field_index)
        
        nex_type = to_nex_type(field_type)
        return nex_type(ir_value)

    def __repr__(self):
        return f"<{type(self).__name__}>"


class DynamicStruct(StructType):
    """
    A StructType created from an IR type without a Python class.
    
    Used by type_from_ir() when wrapping unknown struct values.
    """
    
    @classmethod
    def from_ir(cls, ir_type) -> 'DynamicStruct':
        """
        Create a DynamicStruct from a CIRCT StructType.
        
        Creates an anonymous Struct class with the appropriate fields.
        """

        if not hw.StructType.isinstance(ir_type):
            raise TypeError(f"Expected hw.StructType, got {ir_type}")
        
        struct_type = hw.StructType(ir_type)
        
        # Build annotations from IR type fields
        # get_fields() returns list of (name, type) tuples
        annotations = {}
        for field_name, field_type in struct_type.get_fields():
            annotations[field_name] = NexType.from_ir(field_type)
        
        # Create anonymous class
        class_name = f"Struct_{hash(str(ir_type)) & 0xFFFF:04x}"
        anon_class = type(class_name, (Struct,), {
            '__annotations__': annotations,
            '_cached_type': None,
            '_hw_type': ir_type,
        })
        
        return StructType(anon_class)
