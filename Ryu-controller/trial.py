from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER,MAIN_DISPATCHER
from ryu.lib.packet import ethernet, packet, vlan
from ryu.ofproto import ofproto_v1_3
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
import networkx as nx
import matplotlib.pyplot as plt

class SimpleController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):
        super(SimpleController,self).__init__(*_args, **_kwargs)
        self.topology_api_app = self
        self.net = {}
        self.graph = nx.DiGraph()
        self.count = 0
    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self,ev):
        
        switch = ev.switch
        self.net[switch.dp.id] = switch
        self.graph.add_node(switch.dp.id)
        self.logger.info("[+]\tSwitch %s has joined the network",switch.dp.id)

    @set_ev_cls(event.EventHostAdd)
    def get_host_data(self,ev):
        self.logger.info("[] host added []")   


    @set_ev_cls(event.EventSwitchLeave)
    def del_topology_data(self,ev):
        if self.count == 0:
            self.showing_graph()
            self.count = 1
        switch = ev.switch
        del self.net[switch.dp.id]
        self.logger.info("[-]\tSwitch %s has left the network",switch.dp.id)
    
    @set_ev_cls(event.EventLinkAdd)
    def get_link_data(self,ev):
        link = ev.link
        self.logger.info("[+]\tNew Link detected between %s and %s",link.src.dpid,link.dst.dpid)
        self.graph.add_edge(link.src.dpid,link.dst.dpid)

    @set_ev_cls(ofp_event.EventOFPPacketIn,MAIN_DISPATCHER)
    def packet_in_handler(self,ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)[0]

        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port, actions=actions)
        datapath.send_msg(out)

    def showing_graph(self):
        pos = nx.spring_layout(self.graph)
        nx.draw_networkx_nodes(self.graph,pos,node_size=500)
        nx.draw_networkx_edges(self.graph,pos,width=2)
        nx.draw_networkx_labels(self.graph, pos, font_size=10, font_family='sans-serif')
        plt.axis('off')
        plt.show()

    def startup(self):
        self.showing_graph()