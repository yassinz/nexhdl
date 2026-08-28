"""
Stream Interface (Ready/Valid Protocol based on ESI)

A standard handshaked streaming channel with data, valid, and ready signals.
"""

from typing import Any
from ..core.ports import INPUT, OUTPUT
from ..types.logic import Logic
from ..types.base import NexValue, to_nex_type, NexType
from .base import Interface, InterfacePort, InterfaceHandle, InterfaceRole


class StreamHandle(InterfaceHandle):
    """
    Handle for Stream interfaces in module build().

    Provides:
    - stream.data, stream.valid, stream.ready
    - stream.fire: handshake occurred (valid & ready)
    - stream.push(data, enable)
    - stream.pop(enable)
    - stream.connect(other) / stream >> other
    """

    @property
    def is_output(self) -> bool:
        return self._spec.is_output

    @property
    def is_input(self) -> bool:
        return self._spec.is_input

    @property
    def is_producer(self) -> bool:
        return self.is_output

    @property
    def is_consumer(self) -> bool:
        return self.is_input

    @property
    def fire(self) -> Logic:
        """Handshake complete (valid and ready both high)."""
        return self.valid & self.ready

    def push(self, data: Any, enable: Any = None):
        """
        Drive data onto the stream.

        Args:
            data: Payload to send
            enable: Condition when data is valid (default 1)
        """
        valid_val = Logic[1](1) if enable is None else (
            Logic[1](enable) if isinstance(enable, int) else enable
        )
        self.valid = valid_val
        self.data = data

    def pop(self, enable: Any = None) -> NexValue:
        """
        Signal ready to receive data from the stream.

        Args:
            enable: Condition when ready to accept (default 1)

        Returns:
            The data payload
        """
        ready_val = Logic[1](1) if enable is None else (
            Logic[1](enable) if isinstance(enable, int) else enable
        )
        self.ready = ready_val
        return self.data

    def connect(self, other: 'StreamHandle'):
        """
        Connect a stream source to a stream sink.

        Data and valid flow from source to sink.
        Ready flows from sink to source.
        """
        if not isinstance(other, StreamHandle):
            return super().connect(other)

        # In module IO:
        # An INPUT stream port has readable valid/data and writable ready.
        # An OUTPUT stream port has writable valid/data and readable ready.
        if self.is_input and other.is_output:
            other.valid = self.valid
            other.data = self.data
            self.ready = other.ready
        elif self.is_output and other.is_input:
            self.valid = other.valid
            self.data = other.data
            other.ready = self.ready
        else:
            raise TypeError(
                f"Cannot connect two stream ports with the same role "
                f"({'OUTPUT' if self.is_output else 'INPUT'} >> "
                f"{'OUTPUT' if other.is_output else 'INPUT'}). "
                f"Connect an OUTPUT to an INPUT."
            )

    @classmethod
    def to_esi_channel_type(cls):
        """Get CIRCT !esi.channel<T> type for this stream."""
        from circt.dialects import esi
        port_defs = getattr(cls, '_port_defs', {})
        data_port = port_defs.get('data')
        if data_port is not None:
            circt_inner_type = NexType.to_circt(data_port.type_obj)
            return esi.ChannelType.get(circt_inner_type)
        return None

    def wrap_esi(self, data: Any, valid: Any):
        """Wrap raw data and valid signals into an ESI Channel using circt.dialects.esi.wrap_vr."""
        from circt.dialects import esi
        import circt
        chan_type = self._spec.interface_cls.to_esi_channel_type()
        i1 = circt.ir.IntegerType.get_signless(1)
        raw_val = data.value if hasattr(data, 'value') else data
        val_valid = valid.value if hasattr(valid, 'value') else valid
        chan, ready = esi.wrap_vr(chan_type, i1, raw_val, val_valid)
        return chan, ready

    def unwrap_esi(self, chan_input: Any, ready: Any):
        """Unwrap an ESI Channel into raw data and valid signals using circt.dialects.esi.unwrap_vr."""
        from circt.dialects import esi
        import circt
        port_defs = getattr(self._spec.interface_cls, '_port_defs', {})
        data_port = port_defs.get('data')
        inner_type = NexType.to_circt(data_port.type_obj)
        i1 = circt.ir.IntegerType.get_signless(1)
        raw_ready = ready.value if hasattr(ready, 'value') else ready
        data, valid = esi.unwrap_vr(inner_type, i1, chan_input, raw_ready)
        return data, valid

    def __repr__(self):
        dir_str = "OUTPUT" if self.is_output else "INPUT"
        return f"<StreamHandle '{self._name}' direction={dir_str}>"


class Stream[T](Interface):
    """
    Ready/Valid streaming interface based on CIRCT's ESI dialect.

    Default directions (Producer / Source):
    - valid: OUTPUT (Sender indicates data is valid)
    - ready: INPUT  (Receiver indicates ready for data)
    - data:  OUTPUT (Payload of type T)

    Flipped directions (Consumer / Sink):
    - valid: INPUT
    - ready: OUTPUT
    - data:  INPUT
    """
    _handle_class = StreamHandle

    valid: OUTPUT[Logic[1]]
    ready: INPUT[Logic[1]]
    data:  OUTPUT[T]

    @classmethod
    def to_esi_channel_type(cls):
        """Get CIRCT !esi.channel<T> type."""
        from circt.dialects import esi
        port_defs = getattr(cls, '_port_defs', {})
        data_port = port_defs.get('data')
        if data_port is not None:
            circt_inner_type = NexType.to_circt(data_port.type_obj)
            return esi.ChannelType.get(circt_inner_type)
        return None
