from nexhdl import Module, INPUT, OUTPUT, Logic, Array, Clock, Reset, Reg, Param, Mux, clog2

# 1. Define reusable parameter validators
PositiveInt = Param[int](lambda x: x > 0, "Must be positive")
PowerOfTwo  = Param[int](lambda x: x > 0 and (x & (x - 1)) == 0, "Must be a power of two")

class DotProduct[SIZE: PositiveInt, WIDTH: PositiveInt](Module):
    """
    Computes the dot product of two vectors: sum(a[i] * b[i])
    
    Demonstrates:
    - Precision management: Widening signals for products and sums to avoid overflow.
    - Parameterized logic: Using generic parameters for both dimensions and bit-widths.
    - Combinatorial reduction: Summing an array of generated products.
    """
    a: INPUT[Array[SIZE, Logic[WIDTH]]]
    b: INPUT[Array[SIZE, Logic[WIDTH]]]
    
    # Result width: 2*WIDTH for the product, + log2(SIZE) for the sum accumulation
    res: OUTPUT[Logic[2 * WIDTH + clog2(SIZE)]]

    def build(self, io):
        # Calculate full-precision result width
        product_width = 2 * WIDTH
        result_width = product_width + clog2(SIZE)
        
        # 1. Generate all products
        # We extend operands to product_width before multiplying
        products = []
        for i in range(SIZE):
            prod = io.a[i].zext(product_width) * io.b[i].zext(product_width)
            products.append(prod)
            
        # 2. Sum all products
        # We use a running sum with the full result width
        total = Logic[result_width](0)
        for p in products:
            total = total + p.zext(result_width)
            
        io.res = total

class PipelinedMAC[WIDTH: PositiveInt](Module):
    """
    A Pipelined Multiply-Accumulate (MAC) unit.
    
    Architecture:
    Cycle 0: Inputs a, b sampled
    Cycle 1: Product (a*b) registered
    Cycle 2: Accumulator updated
    """
    clk: INPUT[Clock]
    rst: INPUT[Reset]
    en:  INPUT[Logic[1]]
    clr: INPUT[Logic[1]] # Clear the accumulator
    
    a:   INPUT[Logic[WIDTH]]
    b:   INPUT[Logic[WIDTH]]
    
    # Use a fixed 40-bit accumulator (common in DSPs like TI C6000 or ARM)
    acc: OUTPUT[Logic[40]]

    def build(self, io):
        # Registers for pipelining
        # Stage 1: Multiplier output
        prod_reg = Reg[Logic[40]]()
        
        # Stage 2: Accumulator
        acc_reg = Reg[Logic[40]](reset_value=0)
        
        with io.clk.posedge, io.rst.negedge:
            # --- Stage 1: Multiplication ---
            # Sample and multiply inputs
            prod_reg.next = io.a.zext(40) * io.b.zext(40)
            
            # --- Stage 2: Accumulation ---
            # If clr is active, we start a new accumulation with the previous product
            # Otherwise we add the product to the current accumulator
            next_acc = Mux[Logic[40]](io.clr, prod_reg, acc_reg + prod_reg)
            
            acc_reg.next = Mux[Logic[40]](io.en, next_acc, acc_reg)
                
        io.acc = acc_reg

if __name__ == "__main__":
    print("--- NexHDL DSP Example ---\n")

    # 1. Combinatorial Dot Product
    # Example: 4-element dot product of 8-bit values
    dot = DotProduct[4, 8]()
    print(f"Created: {dot.name}")
    print(dot.verilog())
    
    with dot.simulate() as sim:
        sim.io.a = [1, 2, 3, 4]
        sim.io.b = [10, 20, 30, 40]
        sim.step()
        # Result = 1*10 + 2*20 + 3*30 + 4*40 = 10 + 40 + 90 + 160 = 300
        print(f"Dot Product result: {sim.io.res}")
        assert sim.io.res == 300

    # 2. Pipelined MAC
    mac = PipelinedMAC[16]()
    print(f"\nCreated: {mac.name}")
    print(mac.verilog())
    
    with mac.simulate() as sim:
        sim.io.rst = 0 # Active low reset
        sim.tick()
        sim.io.rst = 1
        sim.io.en = 1
        sim.io.clr = 1 # Clear starting state
        
        # Cycle 1: Feed 10 * 5
        sim.io.a = 10
        sim.io.b = 5
        sim.tick()
        print(f"Cycle 1: Acc={sim.io.acc} (Product 50 is calculating...)")
        
        # Cycle 2: Feed 20 * 2. 
        # Previous inputs (10 * 5) result in 50 reaching prod_reg.
        sim.io.clr = 0
        sim.io.a = 20
        sim.io.b = 2
        sim.tick()
        print(f"Cycle 2: Acc={sim.io.acc} (Result of 10*5 reached accumulator)")
        
        # Cycle 3: Previous inputs (20 * 2) result in 40 reaching prod_reg.
        # Combined with current Acc (50), we expect 90 next.
        sim.io.a = 0
        sim.io.b = 0
        sim.tick()
        print(f"Cycle 3: Acc={sim.io.acc} (Result of 20*2 added to accumulator)")
        
        # Cycle 4: Second product (40) hits acc_reg
        sim.tick()
        print(f"Cycle 4: Acc={sim.io.acc} (Acc = 50 + 40 = 90)")
        
        assert sim.io.acc == 90
        print("\n✓ DSP Simulation Successful!")
