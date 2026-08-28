"""
StreamChannel - Internal point-to-point handshaked channels
"""

from typing import Any
from ..primitives.wire import Wire
from ..types.logic import Logic
from ..types.base import to_nex_type
from .stream import Stream, StreamHandle
from .base import InterfacePort, InterfaceRole


class _ChannelIO:
    """Mock IO container for channel wire handles."""
    def __init__(self, prefix: str, data_wire, valid_wire, ready_wire):
        self._prefix = prefix
        self._signals = {
            f"{prefix}_data": data_wire,
            f"{prefix}_valid": valid_wire,
            f"{prefix}_ready": ready_wire,
        }
        self._data_wire = data_wire
        self._valid_wire = valid_wire
        self._ready_wire = ready_wire

    def __getattr__(self, name: str):
        signals = object.__getattribute__(self, '_signals')
        if name in signals:
            return signals[name]
        raise AttributeError(f"Channel IO has no signal '{name}'")

    def __setattr__(self, name: str, value: Any):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return
        signals = object.__getattribute__(self, '_signals')
        if name in signals:
            wire = signals[name]
            wire.assign = value
            return
        raise AttributeError(f"Channel IO has no signal '{name}'")


class StreamChannelType:
    """Type descriptor for StreamChannel."""
    def __init__(self, data_type):
        self.data_type = to_nex_type(data_type)

    def __call__(self, name: str = "chan"):
        data_wire = Wire[self.data_type]()
        valid_wire = Wire[Logic[1]]()
        ready_wire = Wire[Logic[1]]()

        stream_cls = Stream[self.data_type]

        # Both handles share the same underlying wires via _ChannelIO
        # inp = consumer side (driving valid/data in, reading ready back)
        # out = producer side (reading valid/data, driving ready)
        io_proxy = _ChannelIO(name, data_wire, valid_wire, ready_wire)

        producer_spec = InterfacePort(stream_cls, role=InterfaceRole.OUTPUT)
        consumer_spec = InterfacePort(stream_cls, role=InterfaceRole.INPUT)

        producer_handle = StreamHandle(f"{name}_out", producer_spec, io_proxy)
        consumer_handle = StreamHandle(f"{name}_inp", consumer_spec, io_proxy)

        return StreamChannelInstance(producer_handle, consumer_handle)


class StreamChannelInstance:
    """An instantiated internal channel connecting a producer to a consumer."""
    def __init__(self, out_handle: StreamHandle, inp_handle: StreamHandle):
        self.out = out_handle
        self.inp = inp_handle
        self.producer = out_handle
        self.consumer = inp_handle

    def __repr__(self):
        return f"<StreamChannel out={self.out} inp={self.inp}>"


class StreamChannel:
    """
    Internal point-to-point streaming channel with ready/valid wires.

    Usage:
    ```python
    chan = StreamChannel[Logic[32]]()

    # Submodule 1 drives channel
    mod1.out >> chan.consumer

    # Channel drives Submodule 2
    chan.producer >> mod2.inp
    ```
    """
    def __init__(self):
        raise TypeError("StreamChannel is not instantiable directly. Use StreamChannel[T]()")

    def __class_getitem__(cls, data_type) -> StreamChannelType:
        return StreamChannelType(data_type)
