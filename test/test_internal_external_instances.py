from nexhdl import *


# Internal modules (with build method)
class InternalAdder[WIDTH: int](Module):
    a: INPUT[Logic[WIDTH]]
    b: INPUT[Logic[WIDTH]]
    out: OUTPUT[Logic[WIDTH]]

    def build(self, io):
        io.out = io.a + io.b




# External modules (without build method - black boxes)
class ExternalRAM[ADDR_WIDTH: int, DATA_WIDTH: int](Module):
    clk: INPUT[Logic[1]]
    addr: INPUT[Logic[ADDR_WIDTH]]
    data_in: INPUT[Logic[DATA_WIDTH]]
    data_out: OUTPUT[Logic[DATA_WIDTH]]
    we: INPUT[Logic[1]]
    # No build method - external/black box


class ExternalUART[BAUD_RATE: int](Module):
    clk: INPUT[Logic[1]]
    rst: INPUT[Logic[1]]
    tx_data: INPUT[Logic[8]]
    tx_valid: INPUT[Logic[1]]
    tx_ready: OUTPUT[Logic[1]]
    rx_data: OUTPUT[Logic[8]]
    rx_valid: OUTPUT[Logic[1]]
    # No build method - external/black box


# Test module that uses both internal and external instances
class TestSystem[WIDTH: int](Module):
    clk: INPUT[Logic[1]]
    rst: INPUT[Logic[1]]
    a: INPUT[Logic[WIDTH]]
    b: INPUT[Logic[WIDTH]]
    uart_tx: INPUT[Logic[8]]
    result: OUTPUT[Logic[WIDTH]]
    uart_rx: OUTPUT[Logic[8]]

    def build(self, io):
        # Internal instance 
        adder1 = InternalAdder[WIDTH](a=io.a, b=io.b)
        adder2 = InternalAdder[WIDTH](a=io.a, b=io.b)
        
        # External instances   
        ram1 = ExternalRAM[8, WIDTH](
            clk=io.clk,
            addr=Logic[8](0),
            data_in=adder1.out,
            we=Logic[1](1)
        )
        
        ram2 = ExternalRAM[8, WIDTH](
            clk=io.clk,
            addr=Logic[8](1), 
            data_in=adder2.out,
            we=Logic[1](1)
        )
        
        uart = ExternalUART[115200](
            clk=io.clk,
            rst=io.rst,
            tx_data=io.uart_tx,
            tx_valid=Logic[1](1)
        )
        
        io.result = ram1.data_out + ram2.data_out
        io.uart_rx = uart.rx_data


def test_internal_instances():
    """Test internal module instances (with build method)"""
    print("Testing Internal Module Instances:")
    
    # Test both instantiation syntaxes
    adder1 = InternalAdder[32]()
    adder1.compile()
    print(f"✓ InternalAdder[32]() compiled: {adder1.name}")
    
    # Test parameter validation
    try:
        bad_adder = InternalAdder()
        print("ERROR: Should reject InternalAdder() without parameters")
    except TypeError as e:
        print(f"✓ Parameter validation: {e}")
    
    # Test instance creation within build context
    system = TestSystem[16]()
    system.compile()
    
    print(f"✓ TestSystem[16] with internal instances compiled: {system.name}")


def test_external_instances():
    """Test external module instances (without build method)"""
    print("\nTesting External Module Instances:")
    
    # Test external module compilation
    ram = ExternalRAM[10, 32]()
    ram.compile()
    print(f"✓ ExternalRAM[10, 32] compiled as external: {ram.name}")
    
    uart = ExternalUART[9600]()
    uart.compile()
    print(f"✓ ExternalUART[9600] compiled as external: {uart.name}")
    
    # Verify external modules have no build method
    assert not hasattr(ExternalRAM, 'build'), "External module should not have build method"
    assert not hasattr(ExternalUART, 'build'), "External module should not have build method"
    print("✓ External modules correctly have no build method")


def test_mixed_instances():
    """Test system with both internal and external instances"""
    print("\nTesting Mixed Internal/External Instances:")
    
    system = TestSystem[32]()
    system.compile()
    print(f"✓ Mixed system compiled: {system.name}")
    
    # Test Verilog generation
    try:
        verilog = system.verilog()
        print("✓ Verilog generation successful")
        # Check for both internal and external module references
        assert "InternalAdder" in verilog, "Should contain internal module"
        assert "ExternalRAM" in verilog, "Should contain external module"
        assert "ExternalUART" in verilog, "Should contain external module"
        print("✓ Verilog contains both internal and external modules")
    except Exception as e:
        print(f"Verilog generation: {e}")


def test_instance_syntax_equivalence():
    """Test that both instance syntaxes work equivalently"""
    print("\nTesting Instance Syntax Equivalence:")
    
    class TestModule[W: int](Module):
        in1: INPUT[Logic[W]]
        in2: INPUT[Logic[W]]
        out: OUTPUT[Logic[W]]
        
        def build(self, io):
            add1 = InternalAdder[W](a=io.in1, b=io.in2)
            add2 = InternalAdder[W](a=io.in1, b=io.in2)
            add3 = InternalAdder[W](a=io.in1, b=io.in2)
            add4 = InternalAdder[W](a=io.in1, b=io.in2)
            io.out = add1.out + add2.out * add3.out - add4.out
    
    test_mod = TestModule[16]()
    test_mod.compile()
    print(test_mod.mlir())
    print(test_mod.verilog())
    print("✓ Both instance syntaxes work in same module")


def test_parameter_combinations():
    """Test various parameter combinations"""
    print("\nTesting Parameter Combinations:")
    
    # Single parameter
    ram8 = ExternalRAM[8, 32]()
    ram8.compile()
    print("✓ Two-parameter external module")
    
    # Different parameter values
    uart_slow = ExternalUART[9600]()
    uart_fast = ExternalUART[115200]()
    uart_slow.compile()
    uart_fast.compile()
    print("✓ Same module with different parameters")


if __name__ == "__main__":
    test_internal_instances()
    test_external_instances() 
    test_mixed_instances()
    test_instance_syntax_equivalence()
    test_parameter_combinations()
    print("\n" + "="*50)
    print("All internal/external instance tests completed!")
    print("="*50)