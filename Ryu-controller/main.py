from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER,MAIN_DISPATCHER
from ryu.lib.packet import ethernet, packet, vlan
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.topology import event, switches
from ryu.topology.api import get_all_switch, get_all_link,get_switch, get_link, get_host
import networkx as nx
from networkx.convert import to_dict_of_lists
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import icmp
from ryu.lib import hub
from ryu.ofproto.ofproto_v1_3_parser import OFPPacketOut, OFPActionOutput
import matplotlib.pyplot as plt
import mysql.connector
import copy

class SimpleController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):
        super(SimpleController,self).__init__(*_args, **_kwargs)
        self.topology_api_app = self
        # self.discover_thread = hub.spawn(self._discover)
        self.net = {}
        self.graph = nx.DiGraph()
        self.count = 0
        self.mac_to_port = {}
        self.nodes = {}
        self.links = {}
        self.hosts = {}
        self.topology = nx.DiGraph()
        self.congested_ports = set()

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
        

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        
        self.logger.info('+++ OFP SWITCH FEATRES +++')
        self.logger.info('[+]\tOFPSwitchFeatures received: '
                         '\n\tdatapath_id=%s n_buffers=%d '
                         '\n\tn_tables=%d auxiliary_id=%d '
                         '\n\tcapabilities=0x%08x',
                         msg.datapath_id, msg.n_buffers, msg.n_tables,
                         msg.auxiliary_id, msg.capabilities)

        self.add_flow(datapath, 0, match, actions)

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
                database="SDN"
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

    @set_ev_cls(event.EventSwitchLeave)
    def del_topology_data(self,ev):
        switch = ev.switch
        switch_id = switch.dp.id

        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN"
                )
            mycursor = mydb.cursor()
            mycursor.execute("DELETE FROM SWITCH_TABLE  WHERE switch_id="+str(switch_id)+";")
            print(mycursor.rowcount, "record deleted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        
        self.logger.info("[-]\tSwitch %s has left the network",switch.dp.id)
    
    @set_ev_cls(event.EventHostAdd)
    def get_host_data(self,ev):
        host = ev.host
        mac = host.mac
        switch = host.port.dpid
        port = host.port.port_no
        
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN"
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS HOST_TABLE (mac_address VARCHAR(50),connected_to_switch_id VARCHAR(50),port VARCHAR(20));"
            mycursor.execute(sql)
            sql = "INSERT INTO HOST_TABLE(mac_address,connected_to_switch_id,port) values (%s, %s, %s)"
            val = (str(mac),str(switch),str(port))
            mycursor.execute(sql,val)
            mydb.commit()
            print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

        self.logger.info("[+]\tNew host detected with MAC %s and  switch %s port %s", mac,  switch, port)
        self.graph.add_node(mac,type='host')
        self.graph.add_edge(switch,mac,type='host',port=port)

    @set_ev_cls(event.EventHostDelete)
    def del_host_data(self,ev):
        host = ev.host
        mac = host.mac

        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN"
                )
            mycursor = mydb.cursor()
            mycursor.execute("DELETE FROM HOST_TABLE  WHERE mac_address="+str(mac)+";")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        
        self.logger.info("[-]\tRemoving host detected with MAC %s", mac)
        

    # @set_ev_cls(event.EventPortAdd)
    # def get_port_data(self, ev):
    #     port = ev.port
    #     switch = port.dpid
    #     port_no = port.port_no
    #     self.logger.info("[+]\tNew port detected on switch %s port %s", switch, port_no)
        
    @set_ev_cls(event.EventPortDelete)
    def del_port_data(self,ev):
        port = ev.port
        switch = port.dpid
        port_no = port.port_no
        
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN"
                )
            mycursor = mydb.cursor()
            mycursor.execute("DELETE FROM HOST_TABLE  WHERE connected_to_switch_id="+str(switch)+" AND port="+str(port_no)+";")
            mydb.commit()
            print(mycursor.rowcount, "record deleted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

        self.logger.info("[-]\tDeleting port detected on switch %s port %s", switch, port_no)

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
                database="SDN"
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS LINK_TABLE (src_switch_id VARCHAR(50),src_switch_port VARCHAR(50),dst_switch_id VARCHAR(20),dst_switch_port VARCHAR(20));"
            mycursor.execute(sql)
            sql = "INSERT INTO LINK_TABLE(src_switch_id,src_switch_port,dst_switch_id,dst_switch_port) values (%s, %s, %s,%s)"
            val = (str(src_dpid),str(src_port),str(dst_dpid),str(dst_port))
            mycursor.execute(sql,val)
            mydb.commit()
            print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

        self.re_route(links=link)
        
    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        link = ev.link
        src_dpid = link.src.dpid
        dst_dpid = link.dst.dpid
        src_port = link.src.port_no
        dst_port = link.dst.port_no

        self.logger.info("[-]\tDeleting Link detected between %s - %s and %s - %s",link.src.dpid,src_port,link.dst.dpid,dst_port)
        
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN"
                )
            mycursor = mydb.cursor()
            mycursor.execute("DELETE FROM LINK_TABLE  WHERE src_switch_id="+str(src_dpid)+" AND src_switch_port="+str(src_port)+" AND dst_switch_id="+str(dst_dpid)+" AND dst_switch_port =" + str(dst_port)+ ";")
            mydb.commit()
            print(mycursor.rowcount, "record deleted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

        self.re_route(links=link)
        
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # get Datapath ID to identify OpenFlow switches.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # analyse the received packets using the packet library.
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src

        # get the received port number from packet_in message.
        in_port = msg.match['in_port']

        # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        # if the destination mac address is already learned,
        # decide which port to output the packet, otherwise FLOOD.
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            # Drop the packet instead of flooding it
            actions = []
            out_port = ofproto.OFPP_CONTROLLER

        # construct action list.
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time.
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        # construct packet_out message and send it.
        out = parser.OFPPacketOut(datapath=datapath,
                                buffer_id=ofproto.OFP_NO_BUFFER,
                                in_port=in_port, actions=actions,
                                data=msg.data)
        datapath.send_msg(out)


        
    def showing_graph(self):
        pos = nx.spring_layout(self.graph,k=1, iterations=20)
        nx.draw(self.graph, pos, with_labels=True, node_color='skyblue', node_size=1000, edge_color='gray',width=2)
        nx.draw_networkx_labels(self.graph, pos)
        plt.title("Network topologies from RYU Controller") 
        # plt.savefig('/home/hp/Desktop/fyp/fyp-implem/result/Images/network-topology/" + fig ".png")
        plt.show()

    def startup(self):
        self.showing_graph()

    def get_shortest_path(self,src,dst,G):
        try:
            path = nx.shortest_path(G,src,dst)
            self.logger.info("\n\nShortest path from %s to %s : ", src,dst)
            print(path)
            return path
        except nx.NetworkXNoPath:
            self.logger.warn("\n\nNo path found between %s - %s\n",src,dst)
            return None
        except nx.NetworkXError:
            self.logger.error("Network Error")
            return None
        
    def re_route(self,links):
        src = links.src.dpid
        dst = links.dst.dpid

        link = []
        switch = []

        G = nx.DiGraph()
        self.datapaths = copy.copy(get_switch(self.topology_api_app,None))

        for dp in self.datapaths:
            if dp.dp.id not in G:
                G.add_node(dp.dp.id)
        links = copy.copy(get_link(self, None))
        for link in links:
            G.add_edge(link.src.dpid, link.dst.dpid, port=link.src.port_no)
            G.add_edge(link.dst.dpid, link.src.dpid, port=link.dst.port_no)
        
        adj_list = to_dict_of_lists(G)

        # Print the adjacency list
        for node, neighbors in adj_list.items():
            print(f"{node}: {neighbors}")
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN"
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
                
        path = self.get_shortest_path(src,dst,G)

        # if path is not None:
        #     for i in range(len(path) - 1):
        #         src_dpid = path[i]
        #         dst_dpid = path[i+1]
        #         try:
        #             if src_dpid not in G or dst_dpid not in G:
        #                 continue
        #             in_port = G[src_dpid][dst_dpid]['port']
        #             out_port = G[dst_dpid][src_dpid]['port']
        #             datapath = self.get_datapath(src_dpid)
        #             ofproto = datapath.ofproto
        #             parser = datapath.ofproto_parser
        #             actions = [parser.OFPActionOutput(out_port)]
        #             match = parser.OFPMatch(in_port=in_port)
        #             self.add_flow(datapath=datapath,priority=1,match=match,actions=actions)
        #         except nx.NetworkXException:
        #             print(src_dpid+"\t"+dst_dpid)

    def get_datapath(self,dpid):
        for dp in self.datapaths:
            if dp.dp.id == dpid:
                return dp.dp
        return None
    
    def _discover(self):
        """
        Loop to discover the network topology and update the graph.
        """
        while True:
            # Wait for a switch or link event
            event = hub.Event()
            self.topology_api_app.send_event('TopologyDiscovery', event)
            event.wait()

            # Get the current switch list and link list
            switch_list = copy.copy(get_switch(self.topology_api_app, None))
            link_list = copy.copy(get_link(self.topology_api_app, None))

            # Clear the graph and add nodes and edges
            self.graph.clear()
            self.graph.add_nodes_from(switch.dp.id for switch in switch_list)
            self.graph.add_edges_from((link.src.dpid, link.dst.dpid) for link in link_list)

            # Print the adjacency list
            adj_list = self.graph.adjacency_list()
            print("Adjacency list:")
            for i, neighbors in enumerate(adj_list):
                print(f"Switch {i+1}: {neighbors}")
            print()