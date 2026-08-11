
import pytest
from nexhdl import INPUT, OUTPUT, Logic, Array

class MockPortDirection:
    def __init__(self, type_obj):
        self.type_obj = type_obj

def test_invalid_logic_width():
    # Should fail immediately when creating type
    with pytest.raises(TypeError, match="Logic bit width must be int or parameter"):
        Logic["string"]
        
    with pytest.raises(ValueError, match="Logic bit width must be positive"):
        Logic[0]
        
    with pytest.raises(ValueError, match="Logic bit width must be positive"):
        Logic[-1]

def test_invalid_array_params():
    # Invalid size types
    with pytest.raises(TypeError, match="Array size must be int or parameter"):
        Array["string", Logic[8]]
        
    with pytest.raises(ValueError, match="Array size must be positive"):
        Array[0, Logic[8]]

    # Invalid element types
    with pytest.raises(TypeError, match="Cannot convert to NexType"):
        Array[4, "string"]

if __name__ == "__main__":
    # Manual run for quick verification outside pytest
    try:
        test_invalid_logic_width()
        print("Logic validation passed!")
    except Exception as e:
        print(f"Logic validation failed: {e}")
        
    try:
        test_invalid_array_params()
        print("Array validation passed!")
    except Exception as e:
        print(f"Array validation failed: {e}")
