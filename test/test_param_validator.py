from nexhdl import Module, Logic, Array, INPUT, Param
import pytest



def test_param_validator_module():
    # Define validators
    size_check = Param[int](lambda size: size > 0, "Size must be positive")
    width_check = Param[int](lambda width: width > 0, "Width must be positive")

    class DSP[SIZE: size_check, WIDTH: width_check](Module):
        x: INPUT[Array[SIZE, Logic[WIDTH]]]
        
        def build(self, io):
            pass

    # Valid instantiation should pass
    dsp1 = DSP[16, 32]
    assert dsp1.SIZE == 16
    assert dsp1.WIDTH == 32

    # Wrong type should raise TypeError
    with pytest.raises(TypeError, match="Parameter 'SIZE' must be int, got str"):
        DSP["16", 32]

    # Failed condition should raise ValueError
    with pytest.raises(ValueError, match="Validation failed for parameter 'SIZE': Size must be positive"):
        DSP[0, 32]

    with pytest.raises(ValueError, match="Validation failed for parameter 'WIDTH': Width must be positive"):
        DSP[16, -1]

def test_param_validator_struct():
    from nexhdl import Struct
    
    val_check = Param[int](lambda x: x % 2 == 0, "Must be even")
    
    class EvenPoint[VAL: val_check](Struct):
        x: Logic[VAL]
        y: Logic[VAL]

    # Valid
    p = EvenPoint[8]
    assert p.VAL == 8

    # Invalid type
    with pytest.raises(TypeError):
        EvenPoint[8.0]

    # Invalid value
    with pytest.raises(ValueError, match="Must be even"):
        EvenPoint[7]

def test_param_validator_nested():
    # Test that validation works even when nested
    pos_check = Param[int](lambda x: x > 0, "Must be positive")
    
    class Inner[N: pos_check](Module):
        def build(self, io): pass
        
    class Outer[M: pos_check](Module):
        def build(self, io):
            # If M is used as N, it should still be valid if Outer[M] succeeded
            inner = Inner[M]()

    # Outer[10] is valid
    outer = Outer[10]
    
    # Outer[-1] fails
    with pytest.raises(ValueError):
        Outer[-1]

if __name__ == "__main__":
    test_param_validator_module()
    test_param_validator_struct()
    test_param_validator_nested()

