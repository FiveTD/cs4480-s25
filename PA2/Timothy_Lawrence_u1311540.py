#!/usr/bin/python3

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()

SWITCH_IP = IPAddr('10.0.0.10')
SWITCH_MAC = EthAddr('AA:BB:CC:DD:EE:FF') # Dummy MAC
SERVER_IPS = [IPAddr('10.0.0.5'), IPAddr('10.0.0.6')]

class VirtualLoadBalancer:
    def __init__(self):
        self.serverIndex = 0
        self.connection = None # Set in _handle_ConnectionUp
        
        core.openflow.addListenerByName("ConnectionUp", self._handle_ConnectionUp)
        core.openflow.addListenerByName("PacketIn", self._handle_PacketIn)
        
        log.info("Load balancer started")
    
    def _handle_ConnectionUp(self, event):
        '''Establish connection with the switch.'''
        self.connection = core.openflow.getConnection(event.dpid)
        log.info(f"Connection established with switch {event.dpid}")
    
    def _handle_PacketIn(self, event):
        '''Handle incoming packets and process ARP requests.'''
        log.debug("PacketIn event received")
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
        
        # Get client IP and assign server IP round-robin
        clientIP = arpPkt.protosrc
        serverIP = SERVER_IPS[self.serverIndex]
        self.serverIndex = (self.serverIndex + 1) % len(SERVER_IPS)
        log.info(f"Connecting {clientIP} to {serverIP}")
        
        self._set_flow_rules(clientIP, serverIP, event)
        self._send_arp_reply(arpPkt, event)
        
    def _set_flow_rules(self, clientIP, serverIP, event):
        '''Set flow rules for ICMP packets from `clientIP` to `serverIP` (and vice-versa).'''
        log.debug(f"Setting flow rules for {clientIP} to {serverIP}")
        
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
        
        log.debug(f"Setting flow rules for {serverIP} to {clientIP}")
        
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
    
    def _send_arp_reply(self, arpPkt, event):
        '''Send ARP reply to the client.'''
        log.info("Sending ARP reply")
        
        # Setup reply
        arpReply = pkt.arp()
        arpReply.hwtype = arpPkt.hwtype
        arpReply.prototype = arpPkt.prototype
        arpReply.hwlen = arpPkt.hwlen
        arpReply.protolen = arpPkt.protolen
        arpReply.opcode = pkt.arp.REPLY
        arpReply.hwsrc = SWITCH_MAC
        arpReply.hwdst = arpPkt.hwsrc
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
    
def launch():
    log.info("Starting load balancer")
    VirtualLoadBalancer()
