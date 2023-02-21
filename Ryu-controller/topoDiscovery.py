from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER,MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link,get_all_link
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
import copy
import networkx as nx
import mysql.connector
from networkx.convert import to_dict_of_lists

class MyController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MyController, self).__init__(*args, **kwargs)
        self.topology_api_app = self

        self.G = nx.Graph()

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

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        links = copy.copy(get_link(self,None))
        
        for link in links:
            self.G.add_edge(link.src.dpid, link.dst.dpid, port=link.src.port_no)
            self.G.add_edge(link.dst.dpid, link.src.dpid, port=link.dst.port_no)
        s = ev.link
        self.re_route(links=s)
        # adj_list = to_dict_of_lists(self.G)
        # print("Adj\n")
        # # Print the adjacency list
        # for node, neighbors in adj_list.items():
        #     print(f"{node}: {neighbors}")

    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self,ev):
        self.datapaths = copy.copy(get_switch(self.topology_api_app,None))
        switch = ev.switch
        switch_id = switch.dp.id

        for dp in self.datapaths:
            if dp.dp.id not in self.G:
                self.G.add_node(dp.dp.id)
    
    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        links = ev.link
        self.re_route(links=links)

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
        # try:
        #     mydb = mysql.connector.connect(
        #         host="localhost",
        #         user="root",
        #         password="password",
        #         database="SDN"
        #         )
        #     mycursor = mydb.cursor()
        #     sql = "CREATE TABLE IF NOT EXISTS GRAPH_LINK_TABLE (node VARCHAR(50),connected_to VARCHAR(50));"
        #     mycursor.execute(sql)

        #     sql = "CREATE TABLE IF NOT EXISTS GRAPH_NODE_TABLE (node VARCHAR(50));"
        #     mycursor.execute(sql)

        #     sql = "TRUNCATE GRAPH_NODE_TABLE;"
        #     mycursor.execute(sql)

        #     sql = "TRUNCATE GRAPH_LINK_TABLE;"
        #     mycursor.execute(sql)

        #     for node, neighbors in adj_list.items():
        #         print(f"Node {node}:")
        #         sql = "INSERT INTO GRAPH_NODE_TABLE(node) values (%s)"
        #         val = (str(node))
        #         mycursor.execute(sql,val)
        #         for neighbor, edge_attrs in neighbors.items():
        #             print(f"  Neighbor {neighbor}: {edge_attrs}")
        #             sql = "INSERT INTO GRAPH_LINK_TABLE(node,connected) values (%s, %s)"
        #             val = (str(node),str(neighbor))
        #             mycursor.execute(sql,val)
            
        #     mydb.commit()
        # finally:
        #     if mydb.is_connected():
        #         mycursor.close()
        #         mydb.close()
                
        path = self.get_shortest_path(src,dst,G)

        if path is not None:
            for i in range(len(path) - 1):
                src_dpid = path[i]
                dst_dpid = path[i+1]
                try:
                    if src_dpid not in G or dst_dpid not in G:
                        continue
                    in_port = G[src_dpid][dst_dpid]['port']
                    out_port = G[dst_dpid][src_dpid]['port']
                    datapath = self.get_datapath(src_dpid)
                    ofproto = datapath.ofproto
                    parser = datapath.ofproto_parser
                    actions = [parser.OFPActionOutput(out_port)]
                    match = parser.OFPMatch(in_port=in_port)
                    self.add_flow(datapath=datapath,priority=1,match=match,actions=actions)
                except nx.NetworkXException:
                    print(src_dpid+"\t"+dst_dpid)

    def get_datapath(self,dpid):
        for dp in self.datapaths:
            if dp.dp.id == dpid:
                return dp.dp
        return None