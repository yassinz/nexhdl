"""State extraction and management from Arc IR"""

from dataclasses import dataclass
from circt.support import _walk_with_filter as walk_with_filter
from circt.ir import WalkResult, WalkOrder, Type
from circt.dialects import arc, hw, seq
from circt.ir import IntegerType

# --- Helper Functions for Layout ---

def get_bitwidth(t: Type) -> int:
    """Get logical bit width of a CIRCT type."""
    return 1 if seq.ClockType.isinstance(t) else hw.get_bitwidth(t)


def _align(value: int, align: int) -> int:
    """Round up to next multiple of alignment."""
    return (value + align - 1) // align * align


def get_storage_layout(t: Type) -> tuple[int, int]:
    """
    Compute (size_bytes, align_bytes) for simulator storage.
    Mirrors CIRCT's arc/StateType.cpp computeLLVMBitWidth.
    """
    # Clock: 1 byte, 1-byte aligned
    if seq.ClockType.isinstance(t):
        return 1, 1

    # Integer: ceil(bits/8) bytes, power-of-2 aligned (capped at 16)
    if isinstance(t, IntegerType):
        bits = max(IntegerType(t).width, 8)
        size = (bits + 7) // 8
        align = min(1 << (size - 1).bit_length() if size > 1 else 1, 16)
        return size, align

    # Array: elements at aligned offsets
    if hw.ArrayType.isinstance(t):
        arr = hw.ArrayType(t)
        elem_size, elem_align = get_storage_layout(arr.element_type)
        stride = _align(elem_size, elem_align)
        return arr.size * stride, elem_align

    # Struct: fields at aligned offsets, final size aligned
    if hw.StructType.isinstance(t):
        st = hw.StructType(t)
        size, max_align = 0, 1
        for _, ftype in st.get_fields():
            fsize, falign = get_storage_layout(ftype)
            size = _align(size, falign) + fsize
            max_align = max(max_align, falign)
        return _align(size, max_align), max_align

    # Fallback
    return (get_bitwidth(t) + 7) // 8, 1


# --- Data Classes ---

@dataclass
class PortData:
    name: str
    offset: int
    numbits: int
    type: object
    direction: str

@dataclass
class StateData:
    names: list[str]
    offset: int
    numbits: int
    storage_bytes: int
    type: object

@dataclass
class MemoryData:
    name: str
    offset: int
    stride: int
    depth: int
    msg_type: object
    word_type: object
    word_numbits: int


class StatesInfo:
    def __init__(self, ports, states, memories, size):
        self.ports = {p.name: p for p in ports}
        self.memories = {m.name: m for m in memories}
        self.unique_states = states
        self.size = size
        self.size_bits = self.size * 8
        self.states = {}
        for s in states:
            for name in s.names:
                self.states[name] = s
        self.inputs = {p.name: p for p in ports if p.direction == "input"}
        self.outputs = {p.name: p for p in ports if p.direction == "output"}
        

def get_states_info(module):
    ports = []
    states = []
    memories = []
    size = 0

    collected_ops = []
    def callback(op):
        collected_ops.append(op)
        return WalkResult.ADVANCE

    ops = ["arc.model", "arc.root_input", "arc.alloc_state", "arc.alloc_memory", "arc.root_output"]
    walk_with_filter(module.operation, ops, callback, WalkOrder.POST_ORDER)
        
    for op in collected_ops:
        if op.name == "arc.model":
            if "storageBytes" in op.attributes:
                size = op.attributes['storageBytes'].value
            continue

        offset_bytes = op.attributes['offset'].value
        
        if op.name == "arc.alloc_memory":
            name = op.attributes['name'].value if 'name' in op.attributes else "unnamed_mem"
            stride_bytes = op.attributes['stride'].value
            
            type_str = str(op.results[0].type)
            inner = type_str.split("!arc.memory<")[1].rsplit(",", 1)[0]
            mem_type = Type.parse(f"vector<{inner}>")

            memories.append(MemoryData(
                name=name,
                offset=offset_bytes,
                stride=stride_bytes,
                depth=mem_type.shape[0],
                msg_type=mem_type,
                word_type=mem_type.element_type,
                word_numbits=hw.get_bitwidth(mem_type.element_type)
            ))
            
        elif op.name == "arc.alloc_state":
            t = arc.StateType(op.results[0].type).type
            if "names" not in op.attributes: continue
            
            names = [n.value for n in op.attributes['names']]
            storage_bytes, _ = get_storage_layout(t)
            states.append(StateData(names, offset_bytes, get_bitwidth(t), storage_bytes, t))
            
        elif op.name in ["arc.root_input", "arc.root_output"]:
            name = op.attributes['name'].value
            t = arc.StateType(op.results[0].type).type
            direction = "input" if op.name == "arc.root_input" else "output"
            ports.append(PortData(name, offset_bytes, get_bitwidth(t), t, direction))

    return StatesInfo(ports, states, memories, size)


# --- Byte-Level Serialization ---

def read_value(buf: bytearray, byte_offset: int, t: Type) -> int | list | dict:
    """Read value from bytearray."""
    if seq.ClockType.isinstance(t) or isinstance(t, IntegerType):
        size_bytes, _ = get_storage_layout(t)
        data = buf[byte_offset : byte_offset + size_bytes]
        # LLVM/Host is Little Endian for the integer itself
        return int.from_bytes(data, byteorder='little', signed=False)

    if hw.ArrayType.isinstance(t):
        arr = hw.ArrayType(t)
        elem_size_bytes, elem_align = get_storage_layout(arr.element_type)
        # Element stride is aligned size (matches get_storage_layout for arrays)
        elem_stride = _align(elem_size_bytes, elem_align)
        
        result = []
        for i in range(arr.size):
            # Transform logical index i to CIRCT index (size - 1 - i)
            circt_idx = arr.size - 1 - i
            next_byte_offset = byte_offset + (circt_idx * elem_stride)
            result.append(read_value(buf, next_byte_offset, arr.element_type))
        return result

    if hw.StructType.isinstance(t):
        st = hw.StructType(t)
        result = {}
        current_byte_offset = byte_offset
        
        # MSB-First Packing = Reverse Order for Lower Addresses
        # The last field defined (LSB) sits at the lowest memory address
        for field_name, field_type in reversed(st.get_fields()):
            f_size_bytes, f_align_bytes = get_storage_layout(field_type)
            
            # Align
            padding = (f_align_bytes - (current_byte_offset % f_align_bytes)) % f_align_bytes
            current_byte_offset += padding
            
            result[field_name] = read_value(buf, current_byte_offset, field_type)
            current_byte_offset += f_size_bytes

        result = dict(reversed(result.items()))
        return result

    raise TypeError(f"Unsupported type: {t}")


def write_value(buf: bytearray, byte_offset: int, val, t: Type, name: str = "signal") -> None:
    """Write value to bytearray using native int.to_bytes."""
    if seq.ClockType.isinstance(t) or isinstance(t, IntegerType):
        if not isinstance(val, int):
             raise TypeError(f"Port '{name}' expects int, got {type(val).__name__}")
        
        size_bytes, _ = get_storage_layout(t)
        
        # Ensure buffer is large enough
        if byte_offset + size_bytes > len(buf):
            buf.extend([0] * (byte_offset + size_bytes - len(buf)))

        # Convert negatives to unsigned for storage if needed
        if val < 0:
            # Simple 2s complement check
            bits = size_bytes * 8
            val = (1 << bits) + val

        try:
            val_bytes = val.to_bytes(size_bytes, byteorder='little', signed=False)
        except OverflowError:
            raise ValueError(f"Value {val} too large for {size_bytes} bytes in port '{name}'")

        # Copy bytes into buffer
        buf[byte_offset : byte_offset + size_bytes] = val_bytes
        return

    if hw.ArrayType.isinstance(t):
        if not isinstance(val, (list, tuple)):
            raise TypeError(f"Array '{name}' expects list/tuple")
        
        arr = hw.ArrayType(t)
        elem_size_bytes, elem_align = get_storage_layout(arr.element_type)
        # Element stride is aligned size (matches get_storage_layout for arrays)
        elem_stride = _align(elem_size_bytes, elem_align)
        
        for i, v in enumerate(val):
            if i >= arr.size: break
            # Transform logical index i to CIRCT index (size - 1 - i)
            circt_idx = arr.size - 1 - i
            next_byte_offset = byte_offset + (circt_idx * elem_stride)
            write_value(buf, next_byte_offset, v, arr.element_type, f"{name}[{i}]")
        return

    if hw.StructType.isinstance(t):
        if not isinstance(val, dict):
             raise TypeError(f"Struct '{name}' expects dict")
        
        st = hw.StructType(t)
        current_byte_offset = byte_offset
        
        # MSB-First Packing = Reverse Order for Lower Addresses
        for field_name, field_type in reversed(st.get_fields()):
            if field_name not in val:
                raise ValueError(f"Missing field '{field_name}' in struct '{name}'")
            
            f_size_bytes, f_align_bytes = get_storage_layout(field_type)
            
            # Align
            padding = (f_align_bytes - (current_byte_offset % f_align_bytes)) % f_align_bytes
            current_byte_offset += padding
            
            write_value(buf, current_byte_offset, val[field_name], field_type, f"{name}.{field_name}")
            current_byte_offset += f_size_bytes
        return

    raise TypeError(f"Unsupported type: {t}")