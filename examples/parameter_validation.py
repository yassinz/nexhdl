from nexhdl import Module, INPUT, OUTPUT, Logic, Param, clog2

# 1. Define reusable parameter validators
# Power of 2 validation (ensures sizing is efficient for hardware)
PowerOf2 = Param[int](lambda x: x > 0 and (x & (x - 1)) == 0, "Must be power of 2")

# Specific value set validation
BusWidth = Param[int](lambda x: x in [8, 16, 32, 64], "Width must be 8, 16, 32, or 64")

class AddressDecoder[SIZE: PowerOf2, WIDTH: BusWidth](Module):
    """
    An address decoder that validates its memory window and bus width.
    
    BEST PRACTICE:
    - Use Python 'if' for ELABORATION (static checks, generating different hardware structure).
    - Use NexHDL operators (&, |, +, Mux) for HARDWARE (runtime signal behavior).
    """
    addr:   INPUT[Logic[WIDTH]]
    base:   INPUT[Logic[WIDTH]]
    
    match_:  OUTPUT[Logic[1]]
    offset: OUTPUT[Logic[clog2(SIZE)]]

    def build(self, io):
        # --- ELABORATION LOGIC (Static Python) ---
        # This runs once when the module is instantiated.
        # It can be used to print info or conditionally instantiate hardware.
        if WIDTH >= 32:
            print(f"Elaborating high-performance {WIDTH}-bit decoder...")
        else:
            print(f"Elaborating compact {WIDTH}-bit decoder...")

        # --- HARDWARE LOGIC (NexHDL Signals) ---
        # We do NOT use Python 'if io.addr == ...' here.
        # Instead, we use hardware operators to build gates/comparators.
        
        # Match if: base <= addr < base + SIZE
        # Logic operators create hardware comparators and AND gates.
        io.match_ = (io.addr >= io.base) & (io.addr < (io.base + SIZE))
        
        # Slicing with a static range (clog2(SIZE)) is valid.
        io.offset = io.addr[0:clog2(SIZE)]

if __name__ == "__main__":
    print("--- NexHDL Parameter Validation Example ---\n")

    # 1. SUCCESS: 1KB window on a 32-bit bus
    try:
        decoder = AddressDecoder[1024, 32]()
        print(f"Successfully created: {decoder.name}\n")
        
        with decoder.simulate() as sim:
            sim.io.base = 0x1000
            
            # Inside range
            sim.io.addr = 0x1000 + 42
            sim.step()
            print(f"Addr 0x102A: match={sim.io.match_}, offset={sim.io.offset}")
            assert sim.io.match_ == 1
            assert sim.io.offset == 42

            # Outside range
            sim.io.addr = 0x2000
            sim.step()
            print(f"Addr 0x2000: match={sim.io.match_}")
            assert sim.io.match_ == 0

    except Exception as e:
        print(f"Unexpected failure: {e}")

    # 2. FAILURE: Not a power of 2
    print("\nAttempting to create decoder with SIZE=1000...")
    try:
        AddressDecoder[1000, 32]()
    except ValueError as e:
        print(f"Caught expected error: {e}")

    # 3. FAILURE: Invalid width
    print("\nAttempting to create decoder with WIDTH=24...")
    try:
        AddressDecoder[256, 24]()
    except ValueError as e:
        print(f"Caught expected error: {e}")
