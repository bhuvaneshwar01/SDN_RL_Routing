from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.ofproto import ether
from ryu.lib.packet import arp,tcp,ipv4,lldp,ether_types
from ryu.topology import event
from ryu.topology.api import get_all_switch, get_all_link, get_switch, get_link,get_host
from ryu.lib import dpid as dpid_lib
from ryu.controller import dpset
import copy
import mysql.connector
import networkx as nx
from threading import Lock
from networkx.convert import to_dict_of_lists
from bot_detection import bot_detection


class CongestionDetection(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(CongestionDetection, self).__init__(*args, **kwargs)
        self.switch_ports = {}
        self.port_stats = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, MAIN_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Send request to get port statistics
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

        self.switch_ports[datapath.id] = []
        for port in ev.msg.ports:
            self.switch_ports[datapath.id].append(port.port_no)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto

        for stat in ev.msg.body:
            if stat.port_no in self.switch_ports[datapath.id]:
                self.port_stats[(datapath.id, stat.port_no)] = (stat.rx_packets, stat.rx_bytes)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore LLDP packet
            return

        # Check if the ingress port is congested
        in_port = msg.match['in_port']
        (rx_packets, rx_bytes) = self.port_stats.get((datapath.id, in_port), (0, 0))

        if rx_packets > 100 and rx_bytes > 1000:
            # Ingress port is congested, send a flow_mod message to drop packets
            match = parser.OFPMatch(in_port=in_port)
            actions = []
            instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, instructions=instructions)
            datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        datapath = ev.datapath
        print(str(self.switch_ports))
        if ev.state == DEAD_DISPATCHER and self.switch_ports[datapath.id]:
            del self.switch_ports[datapath.id]
