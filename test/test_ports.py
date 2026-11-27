
import pytest
from nexhdl.core.ports import INPUT, OUTPUT
from nexhdl.types import Logic, Clock, Reset, Array, Struct
from nexhdl.types import to_nex_type
from nexhdl.parameters import ParameterProxy

# Mock for ParameterProxy to test pass-through without importing the real one
# We use the real one now because ParameterResolver checks isinstance
class Point(Struct):
    x: Logic[32]
    y: Logic[32]

def test_valid_nex_types():
    """Test standard NexHDL types."""
    p = INPUT[Logic[8]]
    assert isinstance(p.type_obj, LogicTypeWrapper) or str(p.type_obj) == "Logic[8]"
    
    p = OUTPUT[Array[4, Logic[8]]]
    assert "Array" in str(p.type_obj)

    p = INPUT[Point]
    assert "Struct" in str(p.type_obj) or str(p.type_obj) == "<Point>"

def test_shorthand_types():
    """Test integer shorthand for Logic."""
    p = INPUT[8]
    # Should convert to Logic[8]
    assert str(p.type_obj) == "Logic[8]"
    
    p = OUTPUT[1]
    assert str(p.type_obj) == "Logic[1]"

def test_special_types():
    """Test Clock and Reset types."""
    # Class usage
    p = INPUT[Clock]
    assert str(p.type_obj) == "Clock"
    
    p = INPUT[Reset]
    assert str(p.type_obj) == "Reset"

def test_invalid_types():
    """Test that invalid types raise TypeError."""
    with pytest.raises(TypeError, match="Cannot convert to NexType"):
        div = INPUT[dict]
        
    with pytest.raises(TypeError, match="Cannot convert to NexType"):
        div = INPUT["string"]

def test_parameter_pass_through():
    """Test that ParameterProxy objects are passed through untouched."""
    param = ParameterProxy("WIDTH")
    
    # INPUT[param] logic:
    # Since we use real ParameterProxy, hasattr(evaluate) & hasattr(operations) is true.
    # So it should be passed through.
    p = INPUT[param]
    assert p.type_obj is param

def test_resolve_parameters():
    """Test parameter resolution in ports."""
    param = ParameterProxy("WIDTH")
    p = INPUT[param]
    
    # Resolve with integer -> should become Logic[int]
    # Because internal Logic in __resolve_parameters__ calls to_nex_type(32) -> Logic[32]
    resolved = p.__resolve_parameters__({"WIDTH": 32})
    assert str(resolved.type_obj) == "Logic[32]"


# Helper to inspect potentially wrapped types
# Since we don't know exact string reprs effectively, we do some duck typing in asserts above
class LogicTypeWrapper:
    pass
