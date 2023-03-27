from ryu.base import app_manager
from ryu.controller import ofp_event
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
from sql import sql

UP = 1
DOWN = 0

class SimpleController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):
        super(SimpleController,self).__init__(*_args, **_kwargs)
        self.topology_api_app = self
        self.mac_to_port = {}
        self.net = {}
        self.host_mac_ip = {}
        self.host_to_switch = {}
        self.traffic_data = {}
        self.topology = nx.DiGraph()
        self.bot_ip = set()
        self.flow_to_port = {}
        self.switch_status = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg
        self.logger.info('OFPSwitchFeatures received: '
                         '\n\tdatapath_id=0x%016x n_buffers=%d '
                         '\n\tn_tables=%d auxiliary_id=%d '
                         '\n\tcapabilities=0x%08x',
                         msg.datapath_id, msg.n_buffers, msg.n_tables,
                         msg.auxiliary_id, msg.capabilities)
        
        self.switch_status[msg.datapath_id] = 'active'
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        
        # Delete all flow entries when switch connects
        mod = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE,
                                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                                match=match)
        
        self.add_flow(datapath, 0, match, actions)
    
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

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.switch_status[datapath.id] = 'active'
        elif ev.state == DEAD_DISPATCHER:
            self.switch_status[datapath.id] = 'dead'

    def send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
                                in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=data)
        datapath.send_msg(out)


    def drop_packet(self,ev,in_port,src_mac,dst_mac,src_ip,dst_ip,ip_proto):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        # create an empty action list to drop the packet
        actions = []
        # create a flow entry that matches the packet and drops it
        match = parser.OFPMatch(
            in_port=in_port,
            eth_src=src_mac,
            eth_dst=dst_mac,
            ipv4_src=src_ip,
            ipv4_dst=dst_ip,
            ip_proto=ip_proto
        )
        # add the flow entry to the flow table with priority 1 and the drop action
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_CLEAR_ACTIONS, [])]
        mod = parser.OFPFlowMod(datapath=datapath, match=match, cookie=0, command=ofproto.OFPFC_ADD, priority=1, instructions=inst)
        datapath.send_msg(mod)
        # send an error message to the controller to notify the drop
        err_msg = parser.OFPErrorMsg(datapath=datapath, type_=ofproto.OFPET_BAD_REQUEST, code=ofproto.OFPBRC_BAD_TYPE, data=ev.msg.data)
        datapath.send_msg(err_msg)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        pkt_eth = pkt.get_protocol(ethernet.ethernet)
        src_ip = None
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        dst = eth.dst
        src = eth.src

        self.mac_to_port.setdefault(dpid, {})

        self.mac_to_port[dpid][src] = in_port

        
        if ip_pkt:
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            pkt_len = len(msg.data)
            ip_proto = ip_pkt.proto

            if src_ip in self.traffic_data:
                self.traffic_data[src_ip]['pkts'].append(pkt_len)
                self.traffic_data[src_ip]['dst_ips'].append(dst_ip)
            else:
                self.traffic_data[src_ip] = {'pkts': [pkt_len], 'dst_ips': [dst_ip]}
        


        cluster = self.analyze_traffic()

        if cluster is not None and src_ip is not None:
            for s_ip,data in cluster.items():
                if data['cluster'] == 'bot': 
                    self.bot_ip.add(str(s_ip))
                    sql.insert_bot_data(ip_addr= str(s_ip),mac_addr = self.host_mac_ip[str(s_ip)])
                    
                    # match = parser.OFPMatch(eth_src=src)

                    # actions = []

                    # inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                    #                          actions)]
        

                    # mod = parser.OFPFlowMod(
                    # datapath, command=ofproto.OFPFC_ADD,
                    # priority=1, match=match,instructions=inst)
                    # datapath.send_msg(mod)  
                    # return

                    

        # if len(self.bot_ip) > 0:
        #     print(str(self.bot_ip))     
        
        if pkt_eth:
            dst_mac = pkt_eth.dst
            eth_type = pkt_eth.ethertype
        
            
        # Check if the packet is an LLDP packet
        if eth.ethertype == ether.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        
        pkt_tcp = pkt.get_protocol(tcp.tcp)
        if pkt_tcp:  
            ip_header = pkt.get_protocol(ipv4.ipv4)
            src_ip = ip_header.src
            dst_ip = ip_header.dst
            # src_port = tcp_header.src_port
            # dst_port = tcp_header.dst_port
            # seq_num = tcp_header.seq
            pkt_size = len(pkt)
            # if src_ip in self.traffic_data:
            #     self.traffic_data[src_ip]['pkts'].append(pkt_size)
            #     self.traffic_data[src_ip]['dst_ips'].append(dst_ip)
            # else:
            #     self.traffic_data[src_ip] = {'pkts': [pkt_size], 'dst_ips': [dst_ip]}
            if str(src_ip) in self.bot_ip:
                print("Dropping packet due to detection as bot host from " + str(src_ip))
                match = parser.OFPMatch(in_port=in_port, eth_src=src)
                actions = []
                self.add_flow(datapath, 10, match, actions)
                return
            print(f'TCP packet received: {src_ip} : {self.host_mac_ip[str(src_ip)]}:-> {dst_ip} : {self.host_mac_ip[str(dst_ip)]}')
            # print("Shortest path from " + str(self.host_mac_ip[str(src_ip)]) + " to "+ str(self.host_mac_ip[str(dst_ip)])+" : " )
            self.get_shortest_path(self.host_to_switch[self.host_mac_ip[str(src_ip)]],self.host_to_switch[self.host_mac_ip[str(src_ip)]], self.topology)
        
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            if str(pkt_arp.dst_mac) != "00:00:00:00:00:00":
                # print ("datapath id: "+str(dpid))
                # print ("port: "+str(in_port))
                # print ("pkt_eth.dst: " + str(pkt_eth.dst))
                # print ("pkt_eth.src: " + str(pkt_eth.src))
                # print ("pkt_arp: " + str(pkt_arp))
                # print ("pkt_arp:src_ip: " + str(pkt_arp.src_ip))
                # print ("pkt_arp:dst_ip: " + str(pkt_arp.dst_ip))
                # print ("pkt_arp:src_mac: " + str(pkt_arp.src_mac))
                # print ("pkt_arp:dst_mac: " + str(pkt_arp.dst_mac))
                sql.update_mac_ip_host(mac_address=str(pkt_arp.src_mac),ip_address=str(pkt_arp.src_ip))
                sql.update_mac_ip_host(mac_address=str(pkt_arp.dst_mac),ip_address=str(pkt_arp.dst_ip))
                
                if str(src_ip) in self.bot_ip:
                    print("Dropping packet due to detection as bot host from " + str(src_ip))
                    match = parser.OFPMatch(in_port=in_port, eth_src=src)
                    actions = []
                    self.add_flow(datapath, 10, match, actions)
                    return
                adj_list = to_dict_of_lists(self.topology)
                self.host_mac_ip[ str(pkt_arp.src_ip)] = str(pkt_arp.src_mac)
                self.host_mac_ip[ str(pkt_arp.dst_ip)] = str(pkt_arp.dst_mac)
                # Print the adjacency list
                src_ip = pkt_arp.src_ip
                dst_ip = pkt_arp.dst_ip
                pkt_size = len(pkt)
                # if src_ip in self.traffic_data:
                #     self.traffic_data[src_ip]['pkts'].append(pkt_size)
                #     self.traffic_data[src_ip]['dst_ips'].append(dst_ip)
                # else:
                #     self.traffic_data[src_ip] = {'pkts': [pkt_size], 'dst_ips': [dst_ip]}

                for node, neighbors in adj_list.items():
                    print(f"{node}: {neighbors}")
                print("Shortest path from " + str(pkt_arp.src_mac) + " to "+ str(pkt_arp.dst_mac)+" : " )
                self.get_shortest_path(self.host_to_switch[str(pkt_arp.src_mac)],self.host_to_switch[str(pkt_arp.dst_mac)], self.topology)

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # if src_ip not in self.bot_ip:
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
    
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg = ev.msg 
        dp = msg.datapath

        # Check if port is down
        if msg.reason == dp.ofproto.OFPPR_DELETE:
            port_no = msg.desc.port_no

            # Delete flow entries that use this port
            if port_no in self.flow_to_port:
                match = dp.ofproto_parser.OFPMatch(in_port=port_no) | \
                        dp.ofproto_parser.OFPMatch(out_port=port_no)
                mod = dp.ofproto_parser.OFPFlowMod(datapath=dp, command=dp.ofproto.OFPFC_DELETE,
                                                out_port=dp.ofproto.OFPP_ANY,
                                                out_group=dp.ofproto.OFPG_ANY,
                                                match=match)
                dp.send_msg(mod)
                del self.flow_to_port[port_no]

    @set_ev_cls(event.EventHostAdd)
    def get_host_data(self,ev):
        host = ev.host
        mac = host.mac
        switch = host.port.dpid
        port = host.port.port_no

        print("Host "+str(mac) + " -> " + str(switch) + " -> " + str(port))
        self.host_to_switch[str(mac)] = str(switch)
        
        sql.insert_host_data(mac_address=mac,switch_id=switch,port_no=port)
        if str(mac) not in self.topology:
            self.topology.add_node(str(mac))
            self.topology.add_edge(str(mac),str(switch),port=port)
            self.topology.add_edge(str(switch),str(mac),port=port)


    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self,ev):
        self.datapaths = copy.copy(get_switch(self.topology_api_app,None))
        switch = ev.switch
        self.net[switch.dp.id] = switch
        switch_id = switch.dp.id
        mac_address = switch.dp.address

        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS SWITCH_TABLE (switch_id VARCHAR(50),mac_address VARCHAR(50));"
            mycursor.execute(sql)
            sql = "INSERT INTO SWITCH_TABLE(switch_id,mac_address) values (%s, %s)"
            val = (str(switch_id),str(mac_address))
            mycursor.execute(sql,val)
            mydb.commit()
            print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        self.logger.info("[+]\tSwitch %s has joined the network",switch.dp.id)

        self.topo_raw_switches = copy.copy(get_switch(self, None))
        # The Function get_link(self, None) outputs the list of links.
        self.topo_raw_links = copy.copy(get_link(self, None))
        print("===========================================================")
        print(" \t" + "Current Links:")
        for l in self.topo_raw_links:
            print (" \t\t" + str(l))

        print(" \t" + "Current Switches:")
        for s in self.topo_raw_switches:
            print (" \t\t" + str(s))

        hosts = copy.copy(get_host(self, None))


        G = nx.DiGraph()
        
        for dp in self.topo_raw_switches:
            if dp.dp.id not in G:
                G.add_node(str(dp.dp.id))

        for link in self.topo_raw_links:
            G.add_edge(str(link.src.dpid), str(link.dst.dpid), port=link.src.port_no)
            G.add_edge(str(link.dst.dpid), str(link.src.dpid), port=link.dst.port_no)
        
        adj_list = to_dict_of_lists(G)

        # Print the adjacency list
        for node, neighbors in adj_list.items():
            print(f"{node}: {neighbors}")
        
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "CREATE TABLE IF NOT EXISTS GRAPH_LINK_TABLE (node VARCHAR(50),connected_to VARCHAR(50));"
            mycursor.execute(sql)

            sql = "CREATE TABLE IF NOT EXISTS GRAPH_NODE_TABLE (node VARCHAR(50));"
            mycursor.execute(sql)

            sql = "TRUNCATE GRAPH_NODE_TABLE;"
            mycursor.execute(sql)

            sql = "TRUNCATE GRAPH_LINK_TABLE;"
            mycursor.execute(sql)

            for node, neighbors in adj_list.items():
                # sql = "INSERT INTO GRAPH_NODE_TABLE(node) values (%s)"
                # val = (str(node))
                # mycursor.execute(sql,val)
                for i in neighbors:
                    sql = "INSERT INTO GRAPH_LINK_TABLE(node,connected_to) values (%s, %s)"
                    val = (str(node),str(i))
                    mycursor.execute(sql,val)
                    
            
            mydb.commit()
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
                
        for node, neighbors in adj_list.items():
            for i,j in adj_list.items():
                if node != i:
                    self.get_shortest_path(node,i,G)
        self.topology = G
        print("===========================================================")

    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def handler_switch_leave(self, ev):
        self.logger.info("Not tracking Switches, switch leaved.")
        switch = ev.switch
        switch_id = switch.dp.id

        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            mycursor.execute("DELETE FROM SWITCH_TABLE  WHERE switch_id="+str(switch_id)+";")
            # print(mycursor.rowcount, "record deleted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        
        self.topology.remove_node(str(switch.dp.id))
        self.logger.info("[-]\tSwitch %s has left the network",switch.dp.id)

    @set_ev_cls(event.EventLinkAdd)
    def get_link_data(self,ev):
        link = ev.link
        src_dpid = link.src.dpid
        dst_dpid = link.dst.dpid
        src_port = link.src.port_no
        dst_port = link.dst.port_no

        self.logger.info("[+]\tNew Link detected between %s and %s",link.src.dpid,link.dst.dpid)
        
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS LINK_TABLE (src_switch_id VARCHAR(50),src_switch_port VARCHAR(50),dst_switch_id VARCHAR(20),dst_switch_port VARCHAR(20));"
            mycursor.execute(sql)
            sql = "INSERT INTO LINK_TABLE(src_switch_id,src_switch_port,dst_switch_id,dst_switch_port) values (%s, %s, %s,%s)"
            val = (str(src_dpid),str(src_port),str(dst_dpid),str(dst_port))
            mycursor.execute(sql,val)
            mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        finally:
            # print()
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        
    @set_ev_cls(event.EventLinkDelete, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def link_delete_handler(self, ev):
        link = ev.link
        src_dpid = link.src.dpid
        dst_dpid = link.dst.dpid
        src_port = link.src.port_no
        dst_port = link.dst.port_no


        self.topo_raw_switches = copy.copy(get_switch(self, None))
        # The Function get_link(self, None) outputs the list of links.
        self.topo_raw_links = copy.copy(get_link(self, None))
        print("===========================================================")
        print("After link down between { "+ str(src_dpid) + "} : {" + str(src_port) + "} <-> {" + str(dst_dpid) + "} : {" + str(dst_port) + "} \n\t" + "Current Links:")
        for l in self.topo_raw_links:
            print (" \t\t" + str(l))

        print(" \t" + "Current Switches:")
        for s in self.topo_raw_switches:
            print (" \t\t" + str(s))

        hosts = copy.copy(get_host(self, None))


        G = nx.DiGraph()
        
        for dp in self.topo_raw_switches:
            if dp.dp.id not in G:
                G.add_node(str(dp.dp.id))

        for link in self.topo_raw_links:
            G.add_edge(str(link.src.dpid), str(link.dst.dpid), port=link.src.port_no)
            G.add_edge(str(link.dst.dpid), str(link.src.dpid), port=link.dst.port_no)
        
        adj_list = to_dict_of_lists(G)

        # Print the adjacency list
        for node, neighbors in adj_list.items():
            print(f"{node}: {neighbors}")

        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "CREATE TABLE IF NOT EXISTS GRAPH_LINK_TABLE (node VARCHAR(50),connected_to VARCHAR(50));"
            mycursor.execute(sql)

            sql = "DELETE FROM LINK_TABLE WHERE src_switch_id = " + str(src_dpid) +",src_switch_port="+ str(src_port) +",dst_switch_id = " + str(dst_dpid) +",dst_switch_port = " + str(dst_port) + ";"
            val = (str(src_dpid),str(src_port),str(dst_dpid),str(dst_port))
            
            sql = "CREATE TABLE IF NOT EXISTS GRAPH_NODE_TABLE (node VARCHAR(50));"
            mycursor.execute(sql)

            sql = "TRUNCATE GRAPH_NODE_TABLE;"
            mycursor.execute(sql)

            sql = "TRUNCATE GRAPH_LINK_TABLE;"
            mycursor.execute(sql)

            for node, neighbors in adj_list.items():
                # sql = "INSERT INTO GRAPH_NODE_TABLE(node) values (%s)"
                # val = (str(node))
                # mycursor.execute(sql,val)
                for i in neighbors:
                    sql = "INSERT INTO GRAPH_LINK_TABLE(node,connected_to) values (%s, %s)"
                    val = (str(node),str(i))
                    mycursor.execute(sql,val)
                    
            
            mydb.commit()
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

        self.topology = G
        self.get_shortest_path(str(src_dpid),str(dst_dpid),G)
        print("===========================================================")
        

        
    def get_shortest_path(self,src,dst,G):
        try:
            path = nx.shortest_path(G,src,dst)
            self.logger.info(str(path))
            # print(path)
            return path
        except nx.NetworkXNoPath:
            self.logger.warn("[+]\tNo path found between %s - %s",src,dst)
            return None
        except nx.NetworkXError:
            self.logger.error("Network Error")
            return None
        
    def re_route(self,links):
        src = links.src.dpid
        dst = links.dst.dpid

        link = []
        switch = []

        adj_list = to_dict_of_lists(self.topology)

        # Print the adjacency list
        # for node, neighbors in adj_list.items():
        #     print(f"{node}: {neighbors}")
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "CREATE TABLE IF NOT EXISTS GRAPH_LINK_TABLE (node VARCHAR(50),connected_to VARCHAR(50));"
            mycursor.execute(sql)

            sql = "CREATE TABLE IF NOT EXISTS GRAPH_NODE_TABLE (node VARCHAR(50));"
            mycursor.execute(sql)

            sql = "TRUNCATE GRAPH_NODE_TABLE;"
            mycursor.execute(sql)

            sql = "TRUNCATE GRAPH_LINK_TABLE;"
            mycursor.execute(sql)

            for node, neighbors in adj_list.items():
                # sql = "INSERT INTO GRAPH_NODE_TABLE(node) values (%s)"
                # val = (str(node))
                # mycursor.execute(sql,val)
                for i in neighbors:
                    sql = "INSERT INTO GRAPH_LINK_TABLE(node,connected_to) values (%s, %s)"
                    val = (str(node),str(i))
                    mycursor.execute(sql,val)
                    
            
            mydb.commit()
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
                
        path = self.get_shortest_path(src,dst,self.topology)

    def get_datapath(self,dpid):
        for dp in self.datapaths:
            if dp.dp.id == dpid:
                return dp.dp
        return None
    
    def analyze_traffic(self):
        # Aggregate the traffic data by source IP address
        if len(self.traffic_data) <= 1:
            return
        return bot_detection(traffic_data=self.traffic_data)
        # agg_data = {}
        # for src_ip, data in self.traffic_data.items():
        #     agg_data[src_ip] = {'pkt_count': len(data['pkts']),
        #                         'total_bytes': sum(data['pkts']),
        #                         'dst_ips': list(set(data['dst_ips']))}
        
        # # Calculate the consistency score for each source IP address
        # const_data = {}
        # for src_ip, data in agg_data.items():
        #     pkt_count = data['pkt_count']
        #     total_bytes = data['total_bytes']
        #     dst_ips = data['dst_ips']
        #     dst_count = len(dst_ips)
        #     const_data[src_ip] = {'pkt_count': pkt_count,
        #                         'total_bytes': total_bytes,
        #                         'dst_count': dst_count,
        #                         'const_score': pkt_count/dst_count}
        
        # # Cluster the source IP addresses based on the consistency score
        # cluster_data = {}
        # for src_ip, data in const_data.items():
        #     const_score = data['const_score']
        #     if const_score < 0.5:
        #         cluster = 'bot'
        #     else:
        #         cluster = 'normal'
        #     cluster_data[src_ip] = {'pkt_count': data['pkt_count'],
        #                             'total_bytes': data['total_bytes'],
        #                             'dst_count': data['dst_count'],
        #                             'const_score': const_score,
        #                             'cluster': cluster}
        
        # # Return the cluster data
        # return cluster_data