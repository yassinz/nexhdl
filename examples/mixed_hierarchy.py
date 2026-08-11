from nexhdl import Module, INPUT, OUTPUT, Logic, Clock, Reset, Reg, Mux, clog2

# 1. Internal Module (Logic defined in NexHDL)
class ALU[WIDTH: int](Module):
    """An internal ALU module with its logic defined in Python."""
    a:      INPUT[Logic[WIDTH]]
    b:      INPUT[Logic[WIDTH]]
    op:     INPUT[Logic[1]]
    result: OUTPUT[Logic[WIDTH]]

    def build(self, io):
        # op=0 -> add, op=1 -> sub
        io.result = Mux[Logic[WIDTH]](io.op, io.a - io.b, io.a + io.b)

# 2. External Module (Black Box - No 'build' method)
class ExternalComplexIP[WIDTH: int](Module):
    """
    An external module (black box) that exists in a Verilog library.
    It has no 'build' method, so NexHDL treats it as an interface.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    cmd:    INPUT[Logic[4]]
    data_i: INPUT[Logic[WIDTH]]
    data_o: OUTPUT[Logic[WIDTH]]
    valid:  OUTPUT[Logic[1]]
    # No build() means this is an external reference in generated Verilog.

# 3. Parent Module combining both
class SystemController[WIDTH: int](Module):
    """
    A controller that instantiates both internal (ALU) 
    and external (IP) modules.
    """
    clk:    INPUT[Clock]
    rst:    INPUT[Reset]
    
    val_a:  INPUT[Logic[WIDTH]]
    val_b:  INPUT[Logic[WIDTH]]
    cmd:    INPUT[Logic[4]]
    
    out:    OUTPUT[Logic[WIDTH]]

    def build(self, io):
        # Instantiate Internal ALU
        # We can pass ports by name directly in the constructor
        alu = ALU[WIDTH](
            a  = io.val_a,
            b  = io.val_b,
            op = io.cmd[0]
        )
        
        # Instantiate External IP
        # This will create a module instantiation in the output Verilog
        ip = ExternalComplexIP[WIDTH](
            clk    = io.clk,
            rst    = io.rst,
            cmd    = io.cmd,
            data_i = alu.result
        )
        
        # Connect output
        io.out = ip.data_o

if __name__ == "__main__":
    print("--- NexHDL Internal & External Instance Example ---\n")

    # Create the top-level module
    sys_mod = SystemController[32]()
    
    # 1. Inspect the Verilog
    print("--- Generated Verilog (Showing Instantiations) ---")
    verilog = sys_mod.verilog()
    print(verilog)

    # 2. Key Observations
    print("\n--- Summary ---")
    if "ALU" in verilog and "ExternalComplexIP" in verilog:
        print("✓ Successfully instantiated both internal and external modules.")
        print("✓ ALU definition is generated (it has a build method).")
        print("✓ ExternalComplexIP is only instantiated (it has no build method).")
    
    # Note: External modules cannot be simulated easily in the JIT environment 
    # because they lack an IR definition. They are intended for Verilog backends.
    print("\nNote: External modules are primarily for Verilog code generation.")
    print("They represent pre-existing Verilog IPs or vendor macros.")
