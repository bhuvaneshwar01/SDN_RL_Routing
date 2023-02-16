from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER,MAIN_DISPATCHER
from ryu.lib.packet import ethernet, packet, vlan
from ryu.ofproto import ofproto_v1_3
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link, get_host
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
        self.mac_to_port = {}
        self.nodes = {}
        self.links = {}
        self.hosts = {}

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)
    
    def delete_flow(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for dst in self.mac_to_port[datapath.id].keys():
            match = parser.OFPMatch(eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures,CONFIG_DISPATCHER)
    def switch_features_handler(self,ev):
        msg = ev.msg
        self.logger.info('+++ OFP SWITCH FEATRES +++')
        self.logger.info('[+]\tOFPSwitchFeatures received: '
                         '\n\tdatapath_id=0x%016x n_buffers=%d '
                         '\n\tn_tables=%d auxiliary_id=%d '
                         '\n\tcapabilities=0x%08x',
                         msg.datapath_id, msg.n_buffers, msg.n_tables,
                         msg.auxiliary_id, msg.capabilities)

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)


    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self,ev):
        
        switch = ev.switch
        self.net[switch.dp.id] = switch
        self.graph.add_node(switch.dp.id,type='switch')
        self.logger.info("[+]\tSwitch %s has joined the network",switch.dp.id)

    @set_ev_cls(event.EventHostAdd)
    def get_host_data(self,ev):
        host = ev.host
        mac = host.mac
        switch = host.port.dpid

        self.logger.info("New host detected: MAC %s connected to switch %s", mac, switch)
        self.graph.add_node(str(mac),type='host')

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
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("\tpacket in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            self.logger.info('---- FOUND %s',dst)
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)


    def showing_graph(self):
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, with_labels=True, node_color='skyblue', node_size=1500, edge_color='gray', width=1)
        nx.draw_networkx_labels(self.graph, pos)
        plt.title("Network topologies from RYU Controller")
        plt.show()

    def startup(self):
        self.showing_graph()