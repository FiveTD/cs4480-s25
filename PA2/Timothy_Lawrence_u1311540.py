#!/usr/bin/python3

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()

SWITCH_IP = IPAddr('10.0.0.10')
SERVER_IPS = [
    IPAddr('10.0.0.5'),
    IPAddr('10.0.0.6')
]
SERVER_MACS = [
    EthAddr("00:00:00:00:00:05"),
    EthAddr("00:00:00:00:00:06")
]
SERVER_PORTS = [
    5,
    6
]

class VirtualLoadBalancer:
    def __init__(self):
        self.serverIndex = 0
        self.connection = None # Set in _handle_ConnectionUp
        self.mac_table = {} # MAC address table for ARP requests
        
        core.openflow.addListenerByName("ConnectionUp", self._handle_ConnectionUp)
        core.openflow.addListenerByName("PacketIn", self._handle_PacketIn)
        
        log.info("Load balancer started")
    
    def _handle_ConnectionUp(self, event):
        '''Establish connection with the switch.'''
        self.connection = core.openflow.getConnection(event.dpid)
        log.info(f"Connection established with switch {event.dpid}")
    
    def _handle_PacketIn(self, event):
        '''Handle incoming packets and process ARP requests.'''
        packet = event.parsed
        if not packet.parsed:
            log.warning("Ignoring incomplete packet")
            return
        
        log.debug(f"PacketIn event received from {packet.src}")
        
        if packet.type == packet.ARP_TYPE:
            self._handle_arp(packet, event)
        elif packet.type == packet.IP_TYPE:
            log.debug("Caught IP packet not handled by flow rules")
        # Ignore non-ARP packets
    
    def _handle_arp(self, packet, event):
        '''Handle ARP packets and set up flow rules for ICMP traffic.'''
        log.debug("Handling packet")
        
        arpPkt = packet.find('arp')
        if not arpPkt or arpPkt.opcode != pkt.arp.REQUEST:
            log.warning("Ignoring non-ARP request packet")
            return
        
        if arpPkt.protodst == SWITCH_IP:
            log.debug("Handling ARP request from client")
            
            # Get client IP/Port and assign server round-robin
            clientIP = arpPkt.protosrc
            clientPort = event.port
            serverIP = SERVER_IPS[self.serverIndex]
            serverMAC = SERVER_MACS[self.serverIndex]
            serverPort = SERVER_PORTS[self.serverIndex]
            self.serverIndex = (self.serverIndex + 1) % len(SERVER_IPS)
            
            # Store MAC address for ARP reply
            self.mac_table[clientIP] = arpPkt.hwsrc
            
            self._set_flow_rules(clientIP, serverIP, clientPort, serverPort)
            self._send_client_arp_reply(arpPkt, serverMAC, clientPort)
        if arpPkt.protosrc in SERVER_IPS:
            log.debug("Handling ARP request from server")
            
            clientMAC = self.mac_table.get(arpPkt.protodst)
            if clientMAC is None:
                log.warning("Client MAC address not found in table")
                return
            
            # Send ARP reply
            self._send_server_arp_reply(arpPkt, clientMAC, serverPort)
            
        
    def _set_flow_rules(self, clientIP, serverIP, clientPort, serverPort):
        '''Set flow rules for ICMP packets from `clientIP` to `serverIP` (and vice-versa).'''
        log.info(f"Redirecting {clientIP} to {serverIP}")
        
        log.debug(f"Setting flow rules for {clientIP} to {serverIP}")
        
        # Match ICMP packets from client to server
        clientMsg = of.ofp_flow_mod()
        clientMsg.match.dl_type = pkt.ethernet.IP_TYPE
        clientMsg.match.nw_proto = pkt.ipv4.ICMP_PROTOCOL
        clientMsg.match.nw_src = clientIP
        clientMsg.match.nw_dst = SWITCH_IP
        
        # Redirect to the assigned server
        clientMsg.actions.append(of.ofp_action_nw_addr.set_dst(serverIP))
        clientMsg.actions.append(of.ofp_action_output(port=serverPort))
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
        serverMsg.actions.append(of.ofp_action_output(port=clientPort))
        self.connection.send(serverMsg)
    
    def _send_client_arp_reply(self, arpPkt, serverMAC, clientPort):
        '''Send ARP reply to the client.'''
        log.debug("Sending ARP reply to client")
        
        # Setup reply
        arpReply = pkt.arp()
        arpReply.hwtype = arpPkt.hwtype
        arpReply.prototype = arpPkt.prototype
        arpReply.hwlen = arpPkt.hwlen
        arpReply.protolen = arpPkt.protolen
        arpReply.opcode = pkt.arp.REPLY
        arpReply.hwsrc = serverMAC
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
        clientMsg.actions.append(of.ofp_action_output(port=clientPort))
        self.connection.send(clientMsg)
        
    def _send_server_arp_reply(self, arpPkt, clientMAC, serverPort):
        '''Send ARP reply to the server.'''
        log.debug("Sending ARP reply to server")
        
        # Setup reply
        arpReply = pkt.arp()
        arpReply.hwtype = arpPkt.hwtype
        arpReply.prototype = arpPkt.prototype
        arpReply.hwlen = arpPkt.hwlen
        arpReply.protolen = arpPkt.protolen
        arpReply.opcode = pkt.arp.REPLY
        arpReply.hwsrc = clientMAC
        arpReply.hwdst = arpPkt.hwsrc
        arpReply.protosrc = arpPkt.protodst
        arpReply.protodst = arpPkt.protosrc
        
        # Setup ethernet frame
        ethFrame = pkt.ethernet()
        ethFrame.src = arpReply.hwsrc
        ethFrame.dst = arpPkt.hwsrc
        ethFrame.type = pkt.ethernet.ARP_TYPE
        ethFrame.set_payload(arpReply)
        
        # Send the ARP reply
        serverMsg = of.ofp_packet_out()
        serverMsg.data = ethFrame.pack()
        serverMsg.actions.append(of.ofp_action_output(port=serverPort))
        self.connection.send(serverMsg)
    
def launch():
    log.info("Starting load balancer")
    VirtualLoadBalancer()
