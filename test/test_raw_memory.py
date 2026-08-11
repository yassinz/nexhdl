from nexhdl import *
from random import randrange

from circt.dialects import seq
import circt




class HLMEM(Module):
     clk:      INPUT[Clock]
     rst:      INPUT[Logic[1]]
     we:       INPUT[Logic[1]]
     re:       INPUT[Logic[1]]
     wadr:     INPUT[Logic[2]]
     radr:     INPUT[Logic[2]]
     data:     INPUT[Logic[32]]
     
     out:      OUTPUT[Logic[32]]

     def build(self, io):
          hlmemtype = circt.ir.Type.parse("!seq.hlmem<4xi32>")
          datatype = circt.ir.Type.parse("i32")

          mem = seq.hlmem(hlmemtype, io.clk.value, io.rst.value, 'memory')

          seq.write(mem, [io.wadr.value], io.data.value, io.we.value, 1)
          data = seq.read(datatype, mem, [io.radr.value], 1, rd_en=io.re.value)
          io.out = Logic(data)




class FIRMEM(Module):
     clk:      INPUT[Clock]
     we:       INPUT[Logic[1]]
     re:       INPUT[Logic[1]]
     wadr:     INPUT[Logic[2]]
     radr:     INPUT[Logic[2]]
     data:     INPUT[Logic[32]]
     
     out:      OUTPUT[Logic[32]]

     def build(self, io):
          firmemtype = circt.ir.Type.parse("!seq.firmem<4 x 32>")
          
          ruw = circt.ir.IntegerAttr.get(circt.ir.IntegerType.get_signless(32), 1)
          wuw = circt.ir.IntegerAttr.get(circt.ir.IntegerType.get_signless(32), 1)

          sys_name = circt.ir.StringAttr.get("testtt123")
          mem = seq.firmem(firmemtype, 1, 1, ruw, wuw, name="memory", inner_sym=sys_name)

          seq.firmem_write_port(mem, io.wadr.value, io.clk.value, io.data.value, enable=io.we.value)
          data = seq.firmem_read_port(mem, io.radr.value, io.clk.value, enable=io.re.value)
          io.out = Logic(data)


class FIFO(Module):
     clk:      INPUT[Clock]
     rst:      INPUT[Logic[1]]
     re:      INPUT[Logic[1]]
     we:      INPUT[Logic[1]]
     in_data:  INPUT[Logic[32]]
     
     out_data: OUTPUT[Logic[32]]
     full:     OUTPUT[Logic[1]]
     empty:    OUTPUT[Logic[1]]

     def build(self, io):
          out = circt.ir.Type.parse("i32")
          full = circt.ir.Type.parse("i1")
          empty = circt.ir.Type.parse("i1")
          almostFull = circt.ir.Type.parse("i1")
          almostEmpty = circt.ir.Type.parse("i1")

          fifo = seq.fifo(out,
                          full,
                          empty,
                          almostFull,
                          almostEmpty,
                          io.in_data.value,
                          io.re.value,
                          io.we.value,
                          io.clk.value,
                          io.rst.value,
                          8,
                          rd_latency=1,
                          almost_full_threshold=8,
                          almost_empty_threshold=0)
          print(fifo)

          io.out_data = Logic(fifo[0])
          io.full = Logic(fifo[1])
          io.empty = Logic(fifo[2])




def test_fifo():
     m = FIFO()
     print(m.mlir())
     print(m.verilog())

     with m.simulate() as sim:
          io = sim.io
          for i in range(8):
               io.in_data = i * 10
               io.we = 1
               io.re = 0
               sim.tick()
               print(f"Writing {io.in_data}, full={io.full}, empty={io.empty}")
          
          for i in range(8):
               io.we = 0
               io.re = 1
               sim.tick()
               print(f"Reading {io.out_data}, full={io.full}, empty={io.empty}")
               assert io.out_data == i * 10, f"FIFO failed: read {io.out_data}, expected {i * 10}"

          



def test_firmem():
     m = FIRMEM()

     with m.simulate() as sim:
          io = sim.io
     
          # Write values to memory
          for i in range(4):
               io.clk = 0
               io.we = 1
               io.wadr = i
               io.data = i * 10
               sim.tick()
     
          # Read values from memory
          for i in range(4):
               io.clk = 0
               io.we = 0
               io.re = 1
               io.radr = i
               sim.tick()
     
               expected = i * 10
               print(f"Read from address {i}: {io.out} (expected {expected})")
               assert io.out == expected, f"FIRMEM failed: read {io.out} from address {i}, expected {expected}"





def test_hlmem():
     m = HLMEM()
     print(m.mlir())
     
     with m.simulate() as sim:
          io = sim.io
     
          # Write values to memory
          for i in range(4):
               io.clk = 0
               io.we = 1
               io.wadr = i
               io.data = i * 10
               sim.tick()
     
          # Read values from memory
          for i in range(4):
               io.clk = 0
               io.we = 0
               io.re = 1
               io.radr = i
               sim.tick()
     
               expected = i * 10
               print(f"Read from address {i}: {io.out} (expected {expected})")
               assert io.out == expected, f"HLMEM failed: read {io.out} from address {i}, expected {expected}"





if __name__ == "__main__":
     test_firmem()
     test_hlmem()
     test_fifo()

