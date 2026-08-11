"""
Hardware Map (Exact Match Lookup Table)

A Map provides a hardware lookup table that selects a value based on an exact match of the key.
Supports priority matching if multiple patterns overlap.

Usage:
    # 4-bit keys, 32-bit values
    X = Map[4, 32](
        (0b0001, 10),
        (0b0010, 71),
        (0b0110, 41),
        (0b1110, 56),
        default=0
    )
    
    # Lookup returns 32-bit value
    result = X[io.key]
"""

from ..types.base import NexValue, to_nex_type
from ..types.logic import Logic, LogicType
from .mux import Mux


class Map(NexValue):
    """
    **Hardware Map - Map[K_WIDTH, V_TYPE].**

    Example:
    ```python
    # 4-bit keys, 32-bit values
    X = Map[4, Logic[32]](  # or Map[4, 32]
        (0b0001, 10),
        (0b0010, 71),
        (0b0110, 41),
        (0b1110, 56),
        default=0
    )
    # Lookup returns 32-bit value
    result = X[io.key]

    # 4-bit keys, Array of 4x32-bit values
    X = Map[4, Array[4, 32]](
        (0b0001, arr1),
        (0b0010, arr2),
        (0b0110, arr3),
        (0b1110, arr4),
        default=Array[4, 32]([0, 0, 0, 0])
    )

    # Lookup returns 4x32-bit value
    result = X[io.key]
    ```
    """
    
    def __init__(self, key_type, value_type, keys, values, default=None):
        """
        Initialize Map instance.
        
        Args:
            key_type: The key LogicType
            value_type: The value NexType
            keys: List of Logic keys
            values: List of NexValue values
            default: Optional default value (int or NexValue)
        """
        self._key_type = key_type
        self._value_type = value_type
        self._keys = keys
        self._values = values
        self._default = default
        self._num_entries = len(keys)

    @property
    def value(self):
        """Map has no single value - it represents a lookup operation."""
        raise AttributeError("Map has no single value. Use map[key] to lookup a value.")

    def type_like(self):
        """Return an NexType for values of this map."""
        return self._value_type

    def __getitem__(self, lookup_key) -> NexValue:
        """
        Lookup value by key using exact matching.
        
        Args:
            lookup_key: Logic key to lookup
        
        Returns:
            The matched value, or default
        """
        if not isinstance(lookup_key, Logic):
            raise TypeError(f"Lookup key must be Logic, got {type(lookup_key).__name__}")
        
        if lookup_key.width != self._key_type.bit_width:
            raise TypeError(
                f"Lookup key width mismatch: expected Logic[{self._key_type.bit_width}], "
                f"got Logic[{lookup_key.width}]"
            )

        # Build priority mux chain
        # Start with default value (0 if not provided)
        if self._default is not None:
             default_val = self._default
             if isinstance(default_val, int):
                 # Use value_type to convert int to proper hardware constant
                 default_val = self._value_type(default_val)
             result = default_val
        else:
             result = self._value_type.zero()

        # Work backwards through entries (first entry has highest priority)
        for i in range(self._num_entries - 1, -1, -1):
            key = self._keys[i]
            val = self._values[i]
            
            # Exact match check
            is_match = (lookup_key == key)
            
            # Mux: select this value if it matches, else keep result from later matches
            result = Mux[self._value_type](is_match, val, result)
            
        return result

    @classmethod
    def __class_getitem__(cls, args):
        """Allow Map[key_type, value_type] syntax."""
        if not isinstance(args, tuple) or len(args) != 2:
            raise ValueError(f"Map requires [key_type, value_type], got {args}")
        return MapType(args[0], args[1])

    def set_name(self, name: str) -> None:
        """Set name hint (no-op for Map as it has no single IR value)."""
        self._nex_name = name

    def __repr__(self):
        return f"<Map[{self._key_type}, {self._value_type}] with {self._num_entries} entries>"


class MapType:
    """Type descriptor created by Map[K, V]."""
    
    def __init__(self, key_type, value_type):
        # Normalize key type (int -> LogicType)
        if isinstance(key_type, int):
            self._key_type = LogicType(key_type)
        else:
            self._key_type = to_nex_type(key_type)
            
        # Normalize value type (int width -> LogicType)
        if isinstance(value_type, int):
            self._value_type = LogicType(value_type)
        else:
            self._value_type = to_nex_type(value_type)
            
    def __call__(self, *entries, default=None) -> Map:
        """Create a Map instance from entries."""
        if not entries:
            raise ValueError("Map requires at least one entry")
            
        keys = []
        values = []
        
        for i, entry in enumerate(entries):
            if not isinstance(entry, tuple) or len(entry) != 2:
                 raise TypeError(f"Entry {i} must be a (key, value) tuple")
            
            k, v = entry
            
            # Auto-convert int to hardware constants using normalized types
            if isinstance(k, int):
                k = self._key_type(k)
            
            if isinstance(v, int):
                v = self._value_type(v)
            
            # Type checks
            if not isinstance(k, Logic) or k.width != self._key_type.bit_width:
                raise TypeError(f"Key {i} type mismatch: expected {self._key_type}")
                
            if v.type != self._value_type.type:
                raise TypeError(f"Value {i} type mismatch: expected {self._value_type}")
                
            keys.append(k)
            values.append(v)
            
        return Map(self._key_type, self._value_type, keys, values, default=default)
