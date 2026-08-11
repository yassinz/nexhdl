import tkinter as tk
import threading
import queue
import time
import os

from nexhdl import *
from core import Core


class RISCVTerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("RISC-V Console (0x110000)")
        
        # Dark Terminal Style
        self.text = tk.Text(root, bg="black", fg="#55FF55", insertbackground="white", 
                            font=("Consolas", 13), state="disabled")
        self.text.pack(expand=True, fill="both")
        
        # Queues for Thread Communication
        self.input_queue = queue.Queue() # UI -> Sim
        self.output_queue = queue.Queue() # Sim -> UI

        # Bind Key Events
        self.text.bind("<Key>", self.on_key)
        
        # Start UI Update Loop
        self.update_ui()

    def on_key(self, event):
        # Capture character and put in queue
        if len(event.char) > 0:
            char_code = ord(event.char)
            self.input_queue.put(char_code)
        return "break" # Prevent local echo (Terminal logic handles display)

    def write_char(self, char_code):
        self.output_queue.put(chr(char_code))

    def update_ui(self):
        # Process all pending output from simulation
        while not self.output_queue.empty():
            char = self.output_queue.get_nowait()
            self.text.configure(state="normal")
            self.text.insert("end", char)
            self.text.see("end")
            self.text.configure(state="disabled")
        
        # Schedule next check
        self.root.after(30, self.update_ui)



# --- Simulation Thread ---
def simulation_task(gui):
    import circt
    print("[Sim] Compiling Core...")
    with circt.ir.Context() as ctx, circt.ir.Location.unknown():
        circt.register_dialects(ctx)

        core = Core()
        core.compile()
    
        with core.simulate() as sim:
            print("[Sim] Loading Firmware...")
            
            # Load Binary
            try:
                with open("examples/RV32I/micropython.bin", "rb") as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell() + 4
                    f.seek(0)
                    code = [int.from_bytes(f.read(4), 'little') for _ in range(size // 4)]

            except FileNotFoundError as e:
                print("[Sim] Firmware not found!")
                print(e)
                return
                            
            # Load Program
            sim.memories['RAM'][:len(code)] = code
            
            print("[Sim] Running...")

            
            # Reset and start simulation
            io = sim.io
            io.rst = 0; sim.tick(); io.rst = 1

            while True:
                # 1. Handle Output (Write)
                if io.write:
                    gui.write_char(io.rs2 & 0xFF)
                    sim.tick()
                # 2. Handle Input (Read)
                if io.read:
                    # BLOCK until key is pressed in GUI
                    # This freezes the simulation clock
                    key_val = gui.input_queue.get()
                    
                    # Provide data to Core
                    io.data = key_val
                    sim.tick()
                else:
                    # Normal Execution
                    sim.tick()

# --- Main Entry Point ---
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    
    terminal = RISCVTerminal(root)
    
    # Start Simulation in Background Thread
    sim_thread = threading.Thread(target=simulation_task, args=(terminal,), daemon=True)
    sim_thread.start()
    
    # Start UI Loop
    root.mainloop()