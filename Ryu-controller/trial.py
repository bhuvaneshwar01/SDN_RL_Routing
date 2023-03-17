from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3, ofproto_v1_3_parser
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.topology import event
from ryu.topology.api import get_all_switch, get_all_link, get_switch, get_link
from ryu.lib import dpid as dpid_lib
from ryu.controller import dpset
import copy
from threading import Lock
from topoDiscovery import TopoStructure


UP = 1
DOWN = 0

ETH_ADDRESSES = [0x0802, 0x88CC, 0x8808, 0x8809, 0x0800, 0x86DD, 0x88F7]

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        # USed for learning switch functioning
        self.mac_to_port = {}
        # Holds the topology data and structure
        self.topo_shape = TopoStructure()
        self.done = 0

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg
        self.logger.info('OFPSwitchFeatures received: '
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

    """
    This is called when Ryu receives an OpenFlow packet_in message. The trick is set_ev_cls decorator. This decorator
    tells Ryu when the decorated function should be called.
    """
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id

        port = msg.match['in_port']
        pkt = packet.Packet(data=msg.data)
        #self.logger.info("packet-in: %s" % (pkt,))

        pkt_eth = pkt.get_protocol(ethernet.ethernet)
        if pkt_eth:

            dst_mac = pkt_eth.dst
            eth_type = pkt_eth.ethertype

        # This 'if condition' is for learning the ip and mac addresses of hosts as well as .
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            print ("datapath id: "+str(dpid))
            print ("port: "+str(port))
            print ("pkt_eth.dst: " + str(pkt_eth.dst))
            print ("pkt_eth.src: " + str(pkt_eth.src))
            print ("pkt_arp: " + str(pkt_arp))
            print ("pkt_arp:src_ip: " + str(pkt_arp.src_ip))
            print ("pkt_arp:dst_ip: " + str(pkt_arp.dst_ip))
            print ("pkt_arp:src_mac: " + str(pkt_arp.src_mac))
            print ("pkt_arp:dst_mac: " + str(pkt_arp.dst_mac))

            # Destination and source ip address
            d_ip = pkt_arp.dst_ip
            s_ip = pkt_arp.src_ip

            # Destination and source mac address (HW address)
            d_mac = pkt_arp.dst_mac
            s_mac = pkt_arp.src_mac

            in_port = msg.match['in_port']

            print ("Before ip_cache.ip_to_dpid_port: "+str(self.topo_shape.ip_cache.ip_to_dpid_port))
            # This is where ip address of hosts is learnt.
            resu = self.topo_shape.ip_cache.get_dpid_for_ip(s_ip)
            print("resu: "+str(resu))
            if resu == -1:
                # If there is no entry for ip s_ip then add one
                temp_dict = {"connected_host_mac":s_mac, "sw_port_no":in_port,
                             "sw_port_mac":self.topo_shape.get_hw_address_for_port_of_dpid(in_dpid=dpid, in_port_no=in_port)}
                self.topo_shape.ip_cache.add_dpid_host(in_dpid=dpid, in_host_ip=s_ip, **temp_dict)
            else:
                print("-------------------------------------------")
                # IF there is such an entry for ip address s_ip then just update the values
                self.topo_shape.ip_cache.ip_to_dpid_port[dpid][s_ip]["sw_port_no"] = in_port
                # Updating mac: because a host may get disconnected and new host with same ip but different mac connects
                self.topo_shape.ip_cache.ip_to_dpid_port[dpid][s_ip]["connected_host_mac"] = s_mac
                # get_hw_address_for_port_of_dpid(): gets and mac address of a given port id on specific sw or dpid
                self.topo_shape.ip_cache.ip_to_dpid_port[dpid][s_ip]["sw_port_mac"] = self.topo_shape.get_hw_address_for_port_of_dpid(
                    in_dpid=dpid, in_port_no=in_port)

            print ("After ip_cache.ip_to_dpid_port: "+str(self.topo_shape.ip_cache.ip_to_dpid_port))

            d_resu = self.topo_shape.ip_cache.get_dpid_for_ip(d_ip)
            if d_resu != -1:

                # find_shortest_path(): Finds shortest path starting dpid for all nodes.
                # shortest_path_node: Contains the last node you need to get in order to reach dest from source dpid
                shortest_path_hubs, shortest_path_node = self.topo_shape.find_shortest_path(s=dpid)
                print ("Shortest Path in ARP packet_in starting dpid: {0}".format(dpid))
                print("\tNew shortest_path_hubs: {0}"
                      "\n\tNew shortest_path_node: {1}".format(shortest_path_hubs, shortest_path_node))

                # Based on the ip of the destination the dpid of the switch connected to host ip
                dst_dpid_for_ip = self.topo_shape.ip_cache.get_dpid_for_ip(ip=d_ip)
                print ("found {0} ip connected to dpid {1}".format(d_ip, dst_dpid_for_ip))
                if dst_dpid_for_ip != -1 and dpid != dst_dpid_for_ip:
                    temp_dpid_path = self.topo_shape.find_path(s=dpid, d=dst_dpid_for_ip, s_p_n=shortest_path_node)
                    temp_link_path = self.topo_shape.convert_dpid_path_to_links(dpid_list=temp_dpid_path)
                    reverted_temp_link_path = self.topo_shape.revert_link_list(link_list=temp_link_path)
                    #print("temp_dpid_path: "+str(temp_dpid_path))
                    #print "eth_type:  " +str(eth_type)

                    #self.topo_shape.make_path_between_hosts_in_linklist_for_flood(src_ip=s_ip, dst_ip=d_ip, in_link_path=temp_link_path)
                    #self.topo_shape.make_path_between_hosts_in_linklist_for_flood(src_ip=d_ip, dst_ip=s_ip, in_link_path=reverted_temp_link_path)
                    self.topo_shape.make_path_between_hosts_in_linklist(src_ip=s_ip, dst_ip=d_ip, in_link_path=temp_link_path)
                    self.topo_shape.make_path_between_hosts_in_linklist(src_ip=d_ip, dst_ip=s_ip, in_link_path=reverted_temp_link_path)

                self._handle_arp(datapath=datapath,
                                 port=port,
                                 pkt_ethernet=pkt.get_protocols(ethernet.ethernet)[0],
                                 pkt_arp=pkt_arp,
                                 target_hw_addr=self.topo_shape.ip_cache.get_hw_address_of_host(d_ip),
                                 target_ip_addr=d_ip)
        # This prints list of hw addresses of the port for given dpid
        #print(str(self.topo_shape.get_hw_addresses_for_dpid(in_dpid=dpid)))

    def _handle_arp(self, datapath, port, pkt_ethernet, pkt_arp, target_hw_addr, target_ip_addr):
        # see http://osrg.github.io/ryu-book/en/html/packet_lib.html
        if pkt_arp.opcode != arp.ARP_REQUEST:
            return
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_ethernet.src,
                                           src=target_hw_addr))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=target_hw_addr,
                                 src_ip=target_ip_addr,
                                 dst_mac=pkt_arp.src_mac,
                                 dst_ip=pkt_arp.src_ip))
        self._send_packet(datapath, port, pkt)

    def _send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        self.logger.info("To dpid {0} packet-out {1}".format(datapath.id, pkt))
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)
    ###################################################################################
    """
    The event EventSwitchEnter will trigger the activation of get_topology_data().
    """
    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev):
        self.topo_shape.topo_raw_switches = copy.copy(get_switch(self, None))
        self.topo_shape.topo_raw_links = copy.copy(get_link(self, None))

        self.topo_shape.print_links("EventSwitchEnter")
        self.topo_shape.print_switches("EventSwitchEnter")

    """
    If switch is failed this event is fired
    """
    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def handler_switch_leave(self, ev):
        # Right now it doesn't do anything usefull
        self.logger.info("Not tracking Switches, switch leaved.")

    ###################################################################################
    """
    EventOFPPortStatus: An event class for switch port status notification.
    The bellow handles the event.
    """
    @set_ev_cls(dpset.EventPortModify, MAIN_DISPATCHER)
    def port_modify_handler(self, ev):
        print ("\t #######################")
        self.topo_shape.lock.acquire()
        dp = ev.dp
        port_attr = ev.port
        dp_str = dpid_lib.dpid_to_str(dp.id)
        self.logger.info("\t ***switch dpid=%s"
                         "\n \t port_no=%d hw_addr=%s name=%s config=0x%08x "
                         "\n \t state=0x%08x curr=0x%08x advertised=0x%08x "
                         "\n \t supported=0x%08x peer=0x%08x curr_speed=%d max_speed=%d" %
                         (dp_str, port_attr.port_no, port_attr.hw_addr,
                          port_attr.name, port_attr.config,
                          port_attr.state, port_attr.curr, port_attr.advertised,
                          port_attr.supported, port_attr.peer, port_attr.curr_speed,
                          port_attr.max_speed))

        if port_attr.state == 1:
            tmp_list = []
            first_removed_link = self.topo_shape.link_with_src_and_port(port_attr.port_no, dp.id)
            second_removed_link = self.topo_shape.link_with_dst_and_port(port_attr.port_no, dp.id)

            for i, link in enumerate(self.topo_shape.topo_raw_links):
                if link.src.dpid == dp.id and link.src.port_no == port_attr.port_no:
                    print ("\t Removing link " + str(link) + " with index " + str(i))
                elif link.dst.dpid == dp.id and link.dst.port_no == port_attr.port_no:
                    print ("\t Removing link " + str(link) + " with index " + str(i))
                else:
                    tmp_list.append(link)

            self.topo_shape.topo_raw_links = copy.copy(tmp_list)

            self.topo_shape.print_links(" Link Down")
            print ("\t First removed link: " + str(first_removed_link))
            print ("\t Second removed link: " + str(second_removed_link))

            if first_removed_link is not None and second_removed_link is not None:
                # Find shortest path for source with dpid first_removed_link.src.dpid
                shortest_path_hubs, shortest_path_node = self.topo_shape.find_shortest_path(first_removed_link.src.dpid)
                print ("\t Shortest Path:")
                print("\t\tNew shortest_path_hubs: {0}"
                      "\n\t\tNew shortest_path_node: {1}".format(shortest_path_hubs, shortest_path_node))

                """
                find_backup_path(): Finds the bakcup path (which contains dpids) for the removed link which is
                    called first_removed_link based on shortest_path_node that is given to find_backup_path()
                convert_dpid_path_to_links(): The functions turns the given list of dpid to list of Link objects.
                revert_link_list(): This reverts the links in the list of objects. This is because all the links in the
                    topo are double directed edge.
                """
                result = self.topo_shape.convert_dpid_path_to_links(self.topo_shape.find_backup_path(
                    link=first_removed_link, shortest_path_node=shortest_path_node))
                self.topo_shape.print_input_links(list_links=result)
                reverted_result = self.topo_shape.revert_link_list(link_list=result)
                self.topo_shape.print_input_links(list_links=reverted_result)
                # ToDo: Note that here i assume that each sw has one host connected to it.
                first_sw = self.topo_shape.get_first_sw_dpid_in_linklist(in_linklist=result)
                last_sw = self.topo_shape.get_last_sw_dpid_in_linklist(in_linklist=result)
                first_ip = self.topo_shape.ip_cache.get_ip_addresses_connected_to_dpid(in_dpid=first_sw)[0]
                last_ip = self.topo_shape.ip_cache.get_ip_addresses_connected_to_dpid(in_dpid=last_sw)[0]
                self.topo_shape.make_path_between_hosts_in_linklist(src_ip=first_ip, dst_ip=last_ip, in_link_path=result)
                print ("Second make path")
                print ("src_ip= {0} dst_ip= {1}".format(last_ip, first_ip))
                self.topo_shape.print_input_links((reversed(reverted_result)))
                self.topo_shape.make_path_between_hosts_in_linklist(src_ip=last_ip, dst_ip=first_ip, in_link_path=reverted_result)
        elif port_attr.state == 0:
            self.topo_shape.print_links(" Link Up")
        self.topo_shape.lock.release()