#!/usr/bin/python3

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.lib.addresses import EthAddr, IPAddr
import pox.lib.util as poxutil
import pox.lib.revent as revent
import pox.lib.recoco as recoco

log = core.getLogger()

SWITCH_IP = '10.0.0.10'
SERVER_IPS = ['10.0.0.5', '10.0.0.6']

class VirtualLoadBalancer:
    def __init__(self, connection):
        self.connection = connection
        self.serverIndex = 0
        
        connection.addListeners(self)
        
    def _handle_PacketIn(self, event):
        '''Handle incoming packets and process ARP requests.'''
        packet = event.parsed
        if not packet.parsed:
            log.warning("Ignoring incomplete packet")
            return
        
        if packet.type == packet.ARP_TYPE:
            self._handle_arp(packet, event)
        # Ignore non-ARP packets
    
    def _handle_arp(self, packet, event):
        '''Handle ARP packets and set up flow rules for ICMP traffic.'''
        log.info("Handling packet")
        
        arpPkt = packet.find('arp')
        if not arpPkt or arpPkt.opcode != pkt.arp.REQUEST:
            log.warning("Ignoring non-ARP request packet")
            return
        
        # Assign server IP to client round-robin
        clientIP = arpPkt.protosrc
        serverIP = SERVER_IPS[self.serverIndex]
        self.serverIndex = (self.serverIndex + 1) % len(SERVER_IPS)
        log.info(f"Connecting {clientIP} to {serverIP}")
        
        # === Set flow rules for ICMP packets ===
        # Match ICMP packets from client to server
        clientMsg = of.ofp_flow_mod()
        clientMsg.match.dl_type = pkt.ethernet.IP_TYPE
        clientMsg.match.nw_proto = pkt.ipv4.ICMP_PROTOCOL
        clientMsg.match.nw_src = clientIP
        clientMsg.match.nw_dst = SWITCH_IP
        
        # Redirect to the assigned server
        clientMsg.actions.append(of.ofp_action_nw_addr.set_dst(serverIP))
        clientMsg.actions.append(of.ofp_action_output(port=event.port))
        self.connection.send(clientMsg)
        
        # Match ICMP packets from server to client
        serverMsg = of.ofp_flow_mod()
        serverMsg.match.dl_type = pkt.ethernet.IP_TYPE
        serverMsg.match.nw_proto = pkt.ipv4.ICMP_PROTOCOL
        serverMsg.match.nw_src = serverIP
        serverMsg.match.nw_dst = clientIP
        
        # Rewrite source IP to switch (so client perceives switch as server)
        serverMsg.actions.append(of.ofp_action_nw_addr.set_src(SWITCH_IP))
        serverMsg.actions.append(of.ofp_action_output(port=event.port))
        self.connection.send(serverMsg)
        
        # === Send ARP reply ===
        # Setup reply
        arpReply = pkt.arp()
        arpReply.hwsrc = "AA:BB:CC:DD:EE:FF" # Dummy MAC
        arpReply.hwdst = arpPkt.hwsrc
        arpReply.opcode = pkt.arp.REPLY
        arpReply.protosrc = SWITCH_IP
        arpReply.protodst = arpPkt.protosrc
        
        # Setup ethernet frame
        ethFrame = pkt.ethernet()
        ethFrame.src = arpReply.hwsrc
        ethFrame.dst = arpPkt.hwsrc
        ethFrame.type = pkt.ethernet.ARP_TYPE
        ethFrame.set_payload(arpReply)
        
        # Send the ARP reply
        clientMsg = of.ofp_packet_out()
        clientMsg.data = ethFrame.pack()
        clientMsg.actions.append(of.ofp_action_output(port=event.port))
        self.connection.send(clientMsg)
        

def start_load_balancer(event):
    log.info("Starting load balancer")
    VirtualLoadBalancer(event.connection)
    
def launch():
    core.addListenerByName("ConnectionUp", start_load_balancer)
