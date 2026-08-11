# Simplification Opportunities in `nexhdl/types/*`

Based on the analysis of the codebase, here are concrete areas that can be simplified to improve maintainability and reduce code duplication.

## 1. Eliminate Circular Imports & Central Dispatch in `base.py`

Currently, `base.py` contains hardcoded imports inside methods to avoid circular dependencies. This makes the base module knowledgeable about every specific type, which is an anti-pattern (Open/Closed Principle).

### Current State (`base.py`)
```python
def get_value_class(data_type: NexType):
    from .logic import Logic, LogicType
    from .array import Array, ArrayType
    # ... imports all other types ...
    
    if isinstance(data_type, LogicType): return Logic
    # ... if/else chain ...
```

### Proposed Simplification
Move the knowledge of the value class into the `NexType` itself.

1.  Add an abstract property `value_class` to `NexType`.
2.  Implement it in subclasses (`LogicType`, `ArrayType`, `StructType`).

**Result:** `get_value_class` function can be removed entirely. Usage becomes `data_type.value_class`.

## 2. Consolidate Context Manager Logic (`Clock` & `Reset`)

`Clock` and `Reset` in `clock.py` share identical logic for maintaining a stack of active signals (for implicit context).

### Current State
Both classes duplicate:
- `ACTIVE_STACK = []`
- `__enter__` / `__exit__`
- `get_active()`

### Proposed Simplification
Create a `ScopedSignalMixin` or a base class `ScopedSignal` in `clock.py` or separate utils.

```python
class ScopedSignalMixin:
    _stack: list = []  # define in subclass

    def __enter__(self):
        self._stack.append(self)
        return self

    def __exit__(self, *args):
        self._stack.pop()

    @classmethod
    def get_active(cls):
        return cls._stack[-1] if cls._stack else None
```

## 3. Centralize Integer Range Checking

The logic to check if a Python `int` fits into a hardware bit-width is repeated across `Logic`, `Array`, `Struct`, and `Union`.

### Current State (Repeated 4+ times)
```python
if (v + (v < 0)).bit_length() > width:
    raise ValueError(...)
```

### Proposed Simplification
Add a static utility method, perhaps on `Logic` or `LogicType`.

```python
# In Logic class
@staticmethod
def check_int_fits(value: int, width: int, name: str = "Value"):
    if (value + (value < 0)).bit_length() > width:
        raise ValueError(f"{name} {value} out of range for {width} bits")
```

## 4. Normalize Type Conversion

`to_nex_type` in `base.py` and `ArrayType._normalize_elem_type` do similar things. `ArrayType` and others should rely solely on the central `to_nex_type` function to avoid inconsistent behavior.

## 5. Remove `DynamicUnion` Complexity (If unused)

If `DynamicUnion` is unimplemented and `Union` is effectively a flat `Logic` vector, strict adherence to `hw.UnionType` in `from_ir` might be unnecessary burden.

### Proposal
If the system primarily uses `Logic` for unions:
1.  Implement `DynamicUnion.from_ir` to just return a `LogicType` of the appropriate width (treating the union as an opaque bag of bits).
2.  Or, if full Support is needed, implement it properly. Leaving it as a crashing stub is "complex" in the sense that it creates a trap.

## Summary of Impact

| Change | Files Affected | Benefit |
| :--- | :--- | :--- |
| **Remove `get_value_class`** | `base.py`, all types | Decoupling, removes circular imports |
| **Scoped Signal Mixin** | `clock.py` | Reduces code duplication (DRY) |
| **Int Range Helper** | `logic.py`, `array.py`, `struct.py` | DRY, consistent error messages |
