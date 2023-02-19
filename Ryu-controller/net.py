from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER,MAIN_DISPATCHER
from ryu.lib.packet import ethernet, packet, vlan
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link, get_host
import networkx as nx
import matplotlib.pyplot as plt
import mysql.connector

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


        self.graph.add_node(switch.dp.id,type='switch')
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
        
        del self.net[switch.dp.id]
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
        self.graph.remove_node(mac)

    @set_ev_cls(event.EventPortAdd)
    def get_port_data(self, ev):
        port = ev.port
        switch = port.dpid
        port_no = port.port_no
        self.logger.info("[+]\tNew port detected on switch %s port %s", switch, port_no)
        self.graph.add_node(port_no, type='port')
        self.graph.add_edge(switch, port_no, type='port')
    
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

        self.graph.add_edge(link.src.dpid,link.dst.dpid,type='link')

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
        pos = nx.spring_layout(self.graph,k=1, iterations=20)
        nx.draw(self.graph, pos, with_labels=True, node_color='skyblue', node_size=1000, edge_color='gray',width=2)
        nx.draw_networkx_labels(self.graph, pos)
        plt.title("Network topologies from RYU Controller") 
        # plt.savefig('/home/hp/Desktop/fyp/fyp-implem/result/Images/network-topology/" + fig ".png")
        plt.show()

    def startup(self):
        self.showing_graph()