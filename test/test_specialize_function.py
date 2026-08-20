from nexhdl.parameters import specialize_function
import pytest

def test_specialize_function_globals():
    def dummy():
        return X + 1

    spec_func = specialize_function(dummy, {"X": 41})
    assert spec_func() == 42
    assert spec_func.__name__ == "dummy"
    assert spec_func.__wrapped__ is dummy

def test_specialize_function_closure():
    T = "TypeVar_Placeholder"
    def inner():
        """Docstring for inner."""
        return T

    spec_func = specialize_function(inner, {"T": 32})
    assert spec_func() == 32
    assert spec_func.__name__ == "inner"
    assert spec_func.__doc__ == "Docstring for inner."
    assert spec_func.__wrapped__ is inner
