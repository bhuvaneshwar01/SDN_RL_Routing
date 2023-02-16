from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet.ethernet import ether
import matplotlib.pyplot as plt
from ryu.topology import event
from ryu.topology.api import get_all_switch, get_all_link, get_switch, get_link
from ryu.lib import dpid as dpid_lib
from ryu.controller import dpset
import copy
from threading import Lock
import networkx as nx

class TopologyDiscovery(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _EVENTS = [event.EventSwitchEnter,
               event.EventSwitchLeave, event.EventLinkAdd,
               event.EventLinkDelete]

    def __init__(self, *args, **kwargs):
        super(TopologyDiscovery, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.net = nx.DiGraph()
        self.nodes = {}
        self.links = {}
        self.hosts = {}
    
    def gui_topo(net):
        G = nx.Graph()

        for host in net.hosts:
            G.add_node(host.name, type='host')

        for switch in net.switches:
            G.add_node(switch.name, type='switch')

        for link in net.links:
            G.add_edge(link.intf1.node.name, link.intf2.node.name)

        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=1500, edge_color='gray', width=1)
        nx.draw_networkx_labels(G, pos)
        plt.title("Network topologies")
        plt.show()

    def add_node(self, node):
        if node.is_switch():
            if node.dp.id not in self.net:
                self.net.add_node(node.dp.id)
                self.nodes[node.dp.id] = node
        else:
            if node.port is not None:
                key = (node.port.dpid, node.port.port_no)
                if key not in self.hosts:
                    self.hosts[key] = node
                    self.net.add_node(key)
                    # Add a link from the host to the switch port
                    self.net.add_edge(node.port.dpid, key, port=999)

    def add_link(self, link):
        src = link.src
        dst = link.dst
        if src.dpid in self.net and dst.dpid in self.net:
            self.net.add_edge(src.dpid, dst.dpid, port=src.port_no)

    def delete_link(self, link):
        src = link.src
        dst = link.dst
        if src.dpid in self.net and dst.dpid in self.net:
            self.net.remove_edge(src.dpid, dst.dpid)

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        self.add_node(ev.switch)


    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        self.net.remove_node(ev.switch.dp.id)
        del self.nodes[ev.switch.dp.id]

    @set_ev_cls(event.EventPortAdd)
    def port_add_handler(self, ev):
        self.logger.info("Port added: %s", str(ev))
        port = ev.port
        node = self.nodes.get(port.dpid)
        if node:
            node.ports.append(port)

    @set_ev_cls(event.EventPortDelete)
    def port_delete_handler(self, ev):
        self.logger.info("Port deleted: %s", str(ev))
        port = ev.port
        node = self.nodes.get(port.dpid)
        if node and port in node.ports:
            node.ports.remove(port)

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        self.logger.info("Link added: %s", str(ev))
        link = ev.link
        self.add_link(link)

    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        self.logger.info("Link deleted: %s", str(ev))
        link = ev.link
        self.delete_link(link)