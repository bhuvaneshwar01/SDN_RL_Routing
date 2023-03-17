from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3, ofproto_v1_3_parser
from ryu.lib.packet import packet
from ryu.lib.packet.ethernet import ethernet
from ryu.lib.packet.arp import arp
from ryu.topology import event
from ryu.topology.api import get_all_switch, get_all_link, get_switch, get_link
from ryu.lib import dpid as dpid_lib
from ryu.controller import dpset
import copy
from threading import Lock
from hostcache import HostCache

UP = 1
DOWN = 0

ETH_ADDRESSES = [0x0802, 0x88CC, 0x8808, 0x8809, 0x0800, 0x86DD, 0x88F7]


class TopoStructure(object):
    def __init__(self, *args, **kwargs):
        self.topo_raw_switches = []
        self.topo_raw_links = []
        self.topo_links = []
        # Todo: The lock should be removed later.
        self.lock = Lock()

        # Record where each host is connected to.
        self.ip_cache = HostCache()

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """
        Adds a flow to switch with given datapath. The flow has the given priority. For a given match the flow perform the
        specified given actions.
        :param datapath: Datapath object of a switch
        :param priority: priority of the flow which is going to be installed.
        :param match: A match object for that flow
        :param actions: A list of OFPActionOutput objects for the flow.
        :param buffer_id: Some switches support buffer id
        """
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

    def send_flows_for_path(self, in_link_path):
        """
        Gets list of back up link and then based on them it sends flows to the switch.
        Note that it takes care of nodes in the middle very well. But for the endpoints, it assumes that the
        host is connected to port 1.
        :param in_link_path: List of link objects (a path)
        """
        u_dpids = self.find_unique_dpid_inlinklist(in_link_path)
        visited_dpids = []
        for temp_dpid in u_dpids:
            ports = self.find_ports_for_dpid(temp_dpid, in_link_path)
            if len(ports) == 2:
                visited_dpids.append(temp_dpid)
                match = ofproto_v1_3_parser.OFPMatch(in_port=ports[0])
                actions = [ofproto_v1_3_parser.OFPActionOutput(port=ports[1])]
                self.add_flow(self.get_dp_switch_with_id(temp_dpid), 1, match, actions)
                match = ofproto_v1_3_parser.OFPMatch(in_port=ports[1])
                actions = [ofproto_v1_3_parser.OFPActionOutput(port=ports[0])]
                self.add_flow(self.get_dp_switch_with_id(temp_dpid), 1, match, actions)
            elif len(ports) > 2:
                visited_dpids.append(temp_dpid)
                print("Need to be implemented.")

        end_points = [x for x in u_dpids if x not in visited_dpids]
        if len(end_points) > 2:
            print("There is something wrong. There is two endpoints for a link")

        for temp_dpid_endpoint in end_points:
            other_port = self.find_ports_for_dpid(temp_dpid_endpoint, in_link_path)
            match = ofproto_v1_3_parser.OFPMatch(in_port=1)
            actions = [ofproto_v1_3_parser.OFPActionOutput(port=other_port[0])]
            self.add_flow(self.get_dp_switch_with_id(temp_dpid_endpoint), 1, match, actions)
            match = ofproto_v1_3_parser.OFPMatch()
            actions = [ofproto_v1_3_parser.OFPActionOutput(port=1)]
            self.add_flow(self.get_dp_switch_with_id(temp_dpid_endpoint), 1, match, actions)

    def create_intent(self, src_ip, dest_ip):
        """
        Creates a path (intent) from a host with ip address of ``src_ip`` to the destination host with
        ip address of ``dest_id``. It does so by finding the dpids to connect the two hosts
        intent: Based on onos definition intent is a set of flows send to switches in order
        create a path between two endpoints which is this case it's src_ip and dst_ip.
        :type src_ip: str
        :param src_ip: Ip address of the destination host
        :type dst_ip: str
        :param dst_ip: Ip address of the source host
        """
        # Todo: Test the function
        # Find what dpid is connected to the src and dest hosts
        # Find a shortest path from the src_dpid to dest_dpid
        # Add flow for the shortest path
        # Add flow for the end points using the cache.
        pass

    def make_path_between_hosts_in_linklist(self, src_ip, dst_ip, in_link_path):
        """
        Gets list of back up link and then based on them it sends flows to the switch.
        Note that it takes care of nodes in the middle very well.
        intent: Based on onos definition intent is a set of flows send to switches in order
        create a path between two endpoints which is this case it's src_ip and dst_ip.
        :type src_ip: str
        :param src_ip: Ip address of the destination host
        :type dst_ip: str
        :param dst_ip: Ip address of the source host
        :type in_link_path: list
        :param in_link_path: A list of link objects. Links are only between switches; i.e. no link between switches and hosts are recorded in this list.
        """

        for ind, l in enumerate(in_link_path):
            if ind == 0:
                # The variable ports is a list of ports for switch with dpid equal to temp_dpid which the ports
                # are used in the list of links `in_link_path`
                ports = self.find_ports_for_dpid(l.src.dpid, in_link_path)
                # Mac address of the destination host
                host_eth_dst_addr = self.ip_cache.get_hw_address_of_host(in_ip=dst_ip)
                sw_port_connected_to_src_host = self.ip_cache.get_port_num_connected_to_sw(in_dpid=l.src.dpid, in_ip=src_ip)
                # See http://ryu.readthedocs.org/en/latest/ofproto_v1_3_ref.html
                match = ofproto_v1_3_parser.OFPMatch(in_port=sw_port_connected_to_src_host)
                actions = [ofproto_v1_3_parser.OFPActionOutput(port=ports[0])]
                print("FF: Adding flow to {0} dpid. Match.in_port: {3} Match.eth_dst: {1} Actions.port: {2}".format(
                    l.src.dpid, host_eth_dst_addr, ports[0], sw_port_connected_to_src_host))
                # Gets datapath object of the switch with dpid equal to temp_dpid
                self.add_flow(self.get_dp_switch_with_id(l.src.dpid), 1, match, actions)

            if ind == (len(in_link_path)-1):
                # The variable ports is a list of ports for switch with dpid equal to temp_dpid which the ports
                # are used in the list of links `in_link_path`
                ports = self.find_ports_for_dpid(l.dst.dpid, in_link_path)
                # Mac address of the destination host
                host_eth_dst_addr = self.ip_cache.get_hw_address_of_host(in_ip=dst_ip)
                # THese dont work Todo: fix this
                match = ofproto_v1_3_parser.OFPMatch(in_port=ports[0])
                # The port which destination host is connected to last switch
                sw_port_connected_to_dst_host = self.ip_cache.get_port_num_connected_to_sw(in_dpid=l.dst.dpid, in_ip=dst_ip)
                if sw_port_connected_to_dst_host > 0:
                    actions = [ofproto_v1_3_parser.OFPActionOutput(port=sw_port_connected_to_dst_host)]
                    print("SF: Adding flow to {0} dpid. Match.in_port: {3} Match.eth_dst: {1} Actions.port: {2}".format(
                        l.dst.dpid, host_eth_dst_addr, sw_port_connected_to_dst_host, ports[0]))
                    # Gets datapath object of the switch with dpid equal to temp_dpid
                    self.add_flow(self.get_dp_switch_with_id(l.dst.dpid), 1, match, actions)
                else:
                    print("Port Number if neg")
            else:
                pass
                # Add all flows at once

    def send_midpoint_flows_for_path(self, in_path):
        """
        Gets list of link and then based on them it sends flows only to the switches in the midpoints.
        That is the switch in the middle of path not at the endpoints
        Note that it only takes care of nodes in the middle very well.
        :type in_path: list
        :param in_path: list of link objects which collectively is called a path.
        """
        u_dpids = self.find_unique_dpid_inlinklist(in_path)
        for temp_dpid in u_dpids:
            ports = self.find_ports_for_dpid(temp_dpid, in_path)
            if len(ports) == 2:
                match = ofproto_v1_3_parser.OFPMatch(in_port=ports[0])
                actions = [ofproto_v1_3_parser.OFPActionOutput(port=ports[1])]
                self.add_flow(self.get_dp_switch_with_id(temp_dpid), 1, match, actions)
                match = ofproto_v1_3_parser.OFPMatch(in_port=ports[1])
                actions = [ofproto_v1_3_parser.OFPActionOutput(port=ports[0])]
                self.add_flow(self.get_dp_switch_with_id(temp_dpid), 1, match, actions)
            elif len(ports) > 2:
                print("Need to be implemented.")

    def find_backup_path(self, link, shortest_path_node):
        """
        Based on shortest_path_node, the functions finds a backup path for the link object Link.
        Return a list of dpids that the msg has to go though in order to reach destination.
        :type link: Link Object
        :param link: This would be the link that have been failed.
        :type shortest_path_node: dict
        :param shortest_path_node: A dictionary which contains the last node in the shortest path where each destination is reached from.
        """
        s = link.src.dpid
        d = link.dst.dpid
        if d == s:
            # If destination address and source address is same there is something wrong.
            print("Link Error")
        # The bk_path is a list of DPIDs that the path must go through to reach d from s
        bk_path = []
        bk_path.append(d)
        while d != s:
            if d in shortest_path_node:
                d = shortest_path_node[d]
            bk_path.append(d)

        return bk_path

    def find_path(self, s, d, s_p_n):
        """
        Based on shortest_path_node (s_p_n), the functions finds a shorted path between source s and destination d.
        Where d and s are dpid.
        :param s: dpid of the source
        :type s: int
        :param d: dpid of the destination
        :type d: int
        :param s_p_n: is the out put of the shortest path funtion; i.e. shortest_path_node
        :type s_p_n: dict
        :return: a list of dpids that the msg has to go though in order to reach destination
        """
        if d == s:
            print("Link Error")
        # The found_path is a list of DPIDs that the path must go through to reach d from s
        found_path = []
        found_path.append(d)
        while d != s:
            #print "d: "+str(d)+"   s: "+str(s)
            if d in s_p_n:
                d = s_p_n[d]
            found_path.append(d)

        return found_path

    def revert_link_list(self, link_list):
        """
        This reverts the link object in the link list.
        :rtype : list
        :param link_list: List of link objects
        :return: Returns a list where each link is the reversed of the the original one.
        """
        reverted_list = []
        for l in link_list:
            for ll in self.topo_raw_links:
                if l.dst.dpid == ll.src.dpid and l.src.dpid == ll.dst.dpid:
                    reverted_list.append(ll)
        return reverted_list

    def convert_dpid_path_to_links(self, dpid_list):
        """
        This converts the list of dpids returned from find_backup_path() to a list of link objects.
        :param dpid_list:
        :rtype : object
        """
        dpid_list = list(reversed(dpid_list))
        backup_links = []
        for i, v in enumerate(dpid_list):
            if not i > (len(dpid_list)-1) and not i+1 > (len(dpid_list)-1):
                s = v
                d = dpid_list[i+1]
                for link in self.topo_raw_links:
                    if link.dst.dpid == d and link.src.dpid == s:
                        backup_links.append(link)
        return backup_links

    def print_links(self, func_str=None):
        """
        Uses the built in __str__ function to print the links saved in the class `topo_raw_links`.
        :param func_str: A string which will be printed to help user locate the its prints
        """
        print(" \t" + str(func_str) + ": Current Links:")
        for l in self.topo_raw_links:
            print (" \t\t" + str(l))

    def print_input_links(self, list_links):
        """
        Uses the built in __str__ function to print the links.
        :param list_links: LIst of link objects.
        """
        print(" \t Given Links:")
        for l in list_links:
            print (" \t\t" + str(l))

    def print_switches(self, func_str=None):
        """
        Uses the built in __str__ function to print the links saved in the class `topo_raw_switches`.
        :param func_str: A string which will be printed to help user locate the its prints
        """
        print(" \t" + str(func_str) + ": Current Switches:")
        for s in self.topo_raw_switches:
            print (" \t\t" + str(s))
            print("\t\t\t Printing HW address:")
            for p in s.ports:
                print ("\t\t\t " + str(p.hw_addr))

    def get_hw_addresses_for_dpid(self, in_dpid):
        """
        For a specific dpid of switch it return a list of mac addresses for each port of that sw.
        :param in_dpid: Datapath id of the switch.
        :rtype : list
        """
        list_of_HW_addr = []
        for s in self.topo_raw_switches:
            if s.dp.id == in_dpid:
                for p in s.ports:
                    list_of_HW_addr.append(p.hw_addr)
        return list_of_HW_addr

    def get_hw_address_for_port_of_dpid(self, in_dpid, in_port_no):
        """
        For given port on the given dpid it will return hw address of that port otherwise it will return -1.
        :param in_dpid: Datapath id of the switch
        :param in_port_no: A port number on the switch
        :rtype : int or str
        """
        for s in self.topo_raw_switches:
            # here s is a switch object
            if s.dp.id == in_dpid:
                for p in s.ports:
                    # p is the port object
                    if p.port_no == in_port_no:
                        return p.hw_addr
        return -1

    def get_switches_dpid(self):
        """
        Returns a list of switch dpids.
        The switches are learned when they are joined using dpid.
        :rtype : list
        """
        sw_dpids = []
        for s in self.topo_raw_switches:
            sw_dpids.append(s.dp.id)
        return sw_dpids

    def get_switches_str_dpid(self):
        """
        Returns a list of string dpids of switches.
        :rtype : list
        """
        sw_dpids = []
        for s in self.topo_raw_switches:
            sw_dpids.append(dpid_lib.dpid_to_str(s.dp.id))
        return sw_dpids

    def get_dp_switch_with_id(self, dpid):
        """
        Returns a datapath object with id set to dpid
        :param dpid: Datapath id of the switch
        :rtype : object
        """
        for s in self.topo_raw_switches:
            if s.dp.id == dpid:
                return s.dp
        return None

    def switches_count(self):
        """
        Returns the number of current learned switches
        :rtype : int
        """
        return len(self.topo_raw_switches)

    def bring_up_link(self, link):
        """
        Adds the link to list of raw links
        :rtype : Link
        """
        self.topo_raw_links.append(link)

    def check_link(self, sdpid, sport, ddpid, dport):
        """
        Checks if a link with source dpid of sdpid and source port number of sport is connected to a destination with
        dpid of ddpid and port number of dport.
        :param sdpid: Source datapath id of the switch
        :param sport: Source port number
        :param ddpid: Destination datapath id of the switch
        :param dport: Destination port number
        :rtype : bool
        """
        for i, link in self.topo_raw_links:
            if ((sdpid, sport), (ddpid, dport)) == (
                    (link.src.dpid, link.src.port_no), (link.dst.dpid, link.dst.port_no)):
                return True
        return False

    def find_ports_for_dpid(self, dpid, link_list):
        """
        Returns list of port_no of dpid which is used in a list of link objects.
        Note that the link_list has only one path going through switch with given dpid. So there should be
        no more than two port in the list.
        Note that endpoint must have one port in this list of links. The links between hosts and switches is
        not included in this path (list of links)
        :param dpid: Datapath id of a switch
        :param link_list: List of link objects which combined are called path
        :rtype : list
        """
        port_ids = []
        for l in link_list:
            if l.src.dpid == dpid:
                port_ids.append(l.src.port_no)
            elif l.dst.dpid == dpid:
                port_ids.append(l.dst.port_no)
        return port_ids

    def find_unique_dpid_inlinklist(self, link_list):
        """
        Returns list of unique dpids in a list of links. i.e. any dpid that participated in the path.
        :param link_list: List of Link objects
        :type link_list: list
        :rtype : List
        """
        dp_ids = []
        for l in link_list:
            if l.dst.dpid not in dp_ids:
                dp_ids.append(l.dst.dpid)
            elif l.src.dpid not in dp_ids:
                dp_ids.append(dp_ids.append(dp_ids))
        return dp_ids

    def find_shortest_path(self, s):
        """
        Finds the shortest path from source s to all other nodes.
        :param s: Source Dpid
        :rtype : shortest_path_hubs -> Number of hubs it takes for each destination to reach from source with dpid s.
                 shortest_path_node -> The dpid of last node which a packet must pass in order to reach the destination.
        """
        # I really recommend watching this video: https://www.youtube.com/watch?v=zXfDYaahsNA
        s_count = self.switches_count()
        s_temp = s

        # If you wanna see the prinfs set this to one.
        verbose = 0

        visited = []

        Fereng = []
        Fereng.append(s_temp)

        # Records number of hubs which you can reach the node from specified src
        shortest_path_hubs = {}
        # The last node which you can access the node from. For example: {1,2} means you can reach node 1 from node 2.
        shortest_path_node = {}
        shortest_path_hubs[s_temp] = 0
        shortest_path_node[s_temp] = s_temp
        while s_count > len(visited):
            if verbose == 1: print ("visited in: " + str(visited))
            visited.append(s_temp)
            if verbose == 1: print ("Fereng in: " + str(Fereng))
            if verbose == 1: print ("s_temp in: " + str(s_temp))
            for l in self.find_links_with_src(s_temp):
                if verbose == 1: print( "\t" + str(l))
                if l.dst.dpid not in visited:
                    Fereng.append(l.dst.dpid)
                if verbose == 1: print ("\tAdded {0} to Fereng: ".format(l.dst.dpid))
                if l.dst.dpid in shortest_path_hubs:
                    # Find the minimum o
                    if shortest_path_hubs[l.src.dpid] + 1 < shortest_path_hubs[l.dst.dpid]:
                        shortest_path_hubs[l.dst.dpid] = shortest_path_hubs[l.src.dpid] + 1
                        shortest_path_node[l.dst.dpid] = l.src.dpid
                    else:
                        shortest_path_hubs[l.dst.dpid] = shortest_path_hubs[l.dst.dpid]

                    if verbose == 1: print(
                        "\t\tdst dpid found in shortest_path. Count: " + str(shortest_path_hubs[l.dst.dpid]))
                elif l.src.dpid in shortest_path_hubs and l.dst.dpid not in shortest_path_hubs:
                    if verbose == 1: print("\t\tdst dpid not found bit src dpid found.")
                    shortest_path_hubs[l.dst.dpid] = shortest_path_hubs[l.src.dpid] + 1
                    shortest_path_node[l.dst.dpid] = l.src.dpid
            if verbose == 1:
                print ("shortest_path Hubs: " + str(shortest_path_hubs))
                print ("shortest_path Node: " + str(shortest_path_node))
            if s_temp in Fereng:
                Fereng.remove(s_temp)
            #min_val = min(Fereng)
            if verbose == 1: print ("Fereng out: " + str(Fereng))
            t_dpid = [k for k in Fereng if k not in visited]
            if verbose == 1: print ("Next possible dpids (t_dpid): " + str(t_dpid))

            if len(t_dpid) != 0:
                s_temp = t_dpid[t_dpid.index(min(t_dpid))]

            if verbose == 1: print ("s_temp out: " + str(s_temp))
            if verbose == 1: print( "visited out: " + str(visited) + "\n")
        return shortest_path_hubs, shortest_path_node

    def find_path_from_topo(self,src_dpid, dst_dpid, shortest_path_node):
        """
        Find a path between src and dst based on the shorted path info which is stored on shortest_path_node
        :param src_dpid: Source datapath id
        :param dst_dpid: Destination datapath id
        :param shortest_path_node: This is result of the shortest_path function with source dpid as input
        :rtype : list
        """
        path = []
        now_node = dst_dpid
        last_node = None
        while now_node != src_dpid:
            last_node = shortest_path_node.pop(now_node, None)
            if last_node != None:
                l = self.link_from_src_to_dst(now_node, last_node)
                if l is None:
                    print("Link between {0} and {1} was not found in topo.".format(now_node, last_node))
                else:
                    path.append(l)
                    now_node = last_node
            else:
                print ("Path could not be found")
        return path

    def find_dst_with_src(self, s_dpid):
        """
        Finds the dpids of destinations in the currently learned links where the links' source is s_dpid
        :param s_dpid: Source datapath id
        :rtype : list
        """
        d = []
        for l in self.topo_raw_links:
            if l.src.dpid == s_dpid:
                d.append(l.dst.dpid)
        return d

    def find_links_with_src(self, s_dpid):
        """
        Finds the list of link objects where links' src dpid is s_dpid
        :param s_dpid: Source datapath id
        :rtype : list
        """
        d_links = []
        for l in self.topo_raw_links:
            if l.src.dpid == s_dpid:
                d_links.append(l)
        return d_links

    def link_with_src_dst_port(self, in_port, in_dpid):
        """
        Returns a link object that has in_dpid and in_port as either source or destination dpid and port number.
        :param in_port: Port number
        :param in_dpid: Datapath id of the switch
        :rtype : Link or None
        """
        for l in self.topo_raw_links:
            if (l.src.dpid == in_dpid and l.src.port_no == in_port) or (
                            l.dst.dpid == in_dpid and l.src.port_no == in_port):
                return l
        return None

    def link_from_src_to_dst(self, s_dpid, d_dpid):
        """
        Returns a link object which its source has dpid equal to s_dpid and its destination has dpid equal to d_dpid.
        :param s_dpid: Source dpid
        :param d_dpid: Destination dpid
        :rtype : Link or None
        """
        for l in self.topo_raw_links:
            if l.src.dpid == s_dpid and l.dst.dpid == d_dpid:
                return l
        return None

    def link_with_src_and_port(self, in_port, in_dpid):
        """
        Returns a link object that has in_dpid and in_port as source dpid and port.
        :param in_port: port number of the switch with dpid equal to in_dpid
        :param in_dpid: Datapath id of the source switch
        :rtype : Link
        """
        for l in self.topo_raw_links:
            if (l.src.dpid == in_dpid and l.src.port_no == in_port):
                return l
        return None

    def link_with_dst_and_port(self, in_port, in_dpid):
        """
        Returns a link object that has in_dpid and in_port as destination dpid and port.
        :param in_port: port number of the switch with dpid equal to in_dpid
        :param in_dpid: Datapath id of the destination switch
        :rtype : Link
        """
        for l in self.topo_raw_links:
            if (l.dst.dpid == in_dpid and l.dst.port_no == in_port):
                return l
        return None