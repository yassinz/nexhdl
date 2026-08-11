from nexhdl import *

class IPv4Header(Struct):
    version:  Logic[4]
    ihl:      Logic[4]
    tos:      Logic[8]
    length:   Logic[16]
    id:       Logic[16]
    flags:    Logic[3]
    offset:   Logic[13]
    ttl:      Logic[8]
    proto:    Logic[8]
    checksum: Logic[16]
    src_ip:   Logic[32]
    dst_ip:   Logic[32]

class EthernetFrame(Struct):
    dst_mac: Logic[48]
    src_mac: Logic[48]
    eth_type: Logic[16]
    payload:  Array[5, Logic[32]] # Simplified payload for example

class PacketInspector(Module):
    """
    Demonstrates deep inspection of nested structs.
    """
    clk:      INPUT[Clock]
    rst:      INPUT[Reset]
    frame_in: INPUT[EthernetFrame]
    
    is_ipv4:  OUTPUT[Logic[1]]
    is_google_dns: OUTPUT[Logic[1]]

    def build(self, io):
        # We can view the payload as an IPv4 header
        # (Assuming the payload starts with an IPv4 header)
                
        # Casting the payload to IPv4Header
        ipv4 = IPv4Header(io.frame_in.payload)
        
        # Combinatorial checks
        io.is_ipv4 = (io.frame_in.eth_type == 0x0800)
        io.is_google_dns = (ipv4.dst_ip == 0x08080808)



if __name__ == "__main__":
    dut = PacketInspector()
    
    with dut.simulate() as sim:
        sim.io.rst = 0
        sim.tick()
        sim.io.rst = 1
        
        # Construct a frame
        sim.io.frame_in = {
            "dst_mac": 0x112233445566,
            "src_mac": 0xAABBCCDDEEFF,
            "eth_type": 0x0800, # IPv4
            "payload": [
                0x4500003C, # Ver=4, IHL=5, TOS=0, Len=60
                0x1c464000, # ID, Flags, Offset
                0x4001AFA0, # TTL=64, Proto=1, Checksum
                0xC0A80101, # Src=192.168.1.1
                0x08080808  # Dst=8.8.8.8
            ]
        }
        sim.step()
        
        print(f"Is IPv4: {sim.io.is_ipv4}")
        print(f"Is Google DNS: {sim.io.is_google_dns}")
        
        assert sim.io.is_ipv4 == 1
        assert sim.io.is_google_dns == 1
