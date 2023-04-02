from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
import random
from ryu.base import app_manager

# Define the maximum queue size and the initial RED parameters
MAX_QUEUE_SIZE = 100
MIN_THRESHOLD = 10
MAX_THRESHOLD = 90
DROP_PROBABILITY = 0.0

class RYUController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(RYUController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        # self.monitor_thread = hub.spawn(self._monitor)

        # Initialize the queue size and the queue threshold
        self.queue_size = 0
        self.queue_threshold = MAX_THRESHOLD

        # Initialize the Q-learning table and the RL parameters
        self.q_table = {}
        self.alpha = 0.1
        self.gamma = 0.9
        self.epsilon = 0.1
        self.action_space = [0, 1]
        self.observation_space = [(0, 0), (0, 1), (1, 0), (1, 1)]

    # Function to update the Q-learning table based on the reward
    def update_q_table(self, state, action, reward, next_state):
        # Check if the current state is in the Q-learning table
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0]
        # Calculate the Q-value for the current state and action
        q_value = self.q_table[state][action]
        # Calculate the maximum Q-value for the next state
        max_q_value = max(self.q_table[next_state])
        # Calculate the new Q-value based on the reward and the RL parameters
        new_q_value = (1 - self.alpha) * q_value + self.alpha * (reward + self.gamma * max_q_value)
        # Update the Q-learning table
        self.q_table[state][action] = new_q_value

    # Function to select an action based on the Q-learning table and the RL parameters
    def select_action(self, state):
        # Check if the current state is in the Q-learning table
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0]
        # Choose a random action with probability epsilon
        if random.uniform(0, 1) < self.epsilon:
            action = random.choice(self.action_space)
        # Choose the action with the maximum Q-value for the current state
        else:
            action = self.q_table[state].index(max(self.q_table[state]))
        return action

    # Function to update the RED parameters based on the queue size and the queue threshold
    def update_red_parameters(self):
        # Calculate the average queue length
        avg_queue_length = float(self.queue_size) / float(MAX_QUEUE_SIZE)
        # Calculate the drop probability based on the current RED parameters and the average queue length
        drop_probability = (avg_queue_length - float(self.queue_threshold) / 100.0) / 2.0
        drop_probability = max(0.0, min(drop_probability, 1.0))
        global DROP_PROBABILITY
        # Update the RED parameters
        DROP_PROBABILITY = drop_probability


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

        self.mac_to_port.setdefault(datapath.id,{})
        self.datapaths[datapath.id] = datapath

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        
        # Delete all flow entries when switch connects
        mod = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE,
                                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                                match=match)
        
        self.add_flow(datapath, 0, match, actions)


    # Function to handle the OpenFlow packet-in message
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        # Parse the packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        # Check if the packet is an IPv4 TCP packet
        # if eth.ethertype == ether_types.ETH_TYPE_IP and ipv4_pkt and ipv4_pkt.proto == inet.IPPROTO_TCP:
        if ipv4_pkt and tcp_pkt: 
            

            # Calculate the packet size
            packet_size = len(pkt)

            # Update the queue size
            self.queue_size += packet_size

            # Check if the queue size exceeds the maximum queue size
            if self.queue_size > MAX_QUEUE_SIZE:
                # Drop the packet with a certain probability
                if random.uniform(0, 1) < DROP_PROBABILITY:
                    self.queue_size -= packet_size
                    return
                # Remove the oldest packet from the queue
                self.queue_size -= self.packet_queue[0]
                del self.packet_queue[0]

            # Add the packet to the queue
            self.packet_queue.append(packet_size)

            # Choose an action based on the current queue size and the queue threshold
            if float(self.queue_size) / float(MAX_QUEUE_SIZE) < float(self.queue_threshold) / 100.0:
                action = 0
            else:
                action = 1

            # Select the next state based on the action
            next_state = self.observation_space[action]

            # Choose an action based on the Q-learning table and the RL parameters
            state = self.observation_space[action]
            action = self.select_action(state)

            # Calculate the reward based on the action
            if action == 0:
                reward = 1.0
            else:
                reward = -1.0

            # Update the Q-learning table based on the reward
            self.update_q_table(state, action, reward, next_state)

            # Update the RED parameters based on the queue size and the queue threshold
            self.update_red_parameters()

            # Install the flow entry based on the action
            if action == 0:
                actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            else:
                actions = []
            match = parser.OFPMatch(in_port=in_port, eth_type=eth.ethertype,
                                    ipv4_src=ipv4_pkt.src, ipv4_dst=ipv4_pkt.dst,
                                    tcp_src=tcp_pkt.src_port, tcp_dst=tcp_pkt.dst
                                            )
            self.add_flow(datapath, 1, match, actions)

            # Send the packet to the selected port
            if action == 0:
                out_port = ofproto.OFPP_FLOOD
            else:
                out_port = ofproto.OFPP_LOCAL
            actions = [parser.OFPActionOutput(out_port)]
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                    in_port=in_port, actions=actions,
                                    data=msg.data)
            datapath.send_msg(out)

    # Function to add a flow entry to the OpenFlow switch
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Create a flow mod message
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    # Function to select an action based on the current state and the Q-learning table
    def select_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            # Select a random action
            action = random.choice(self.action_space)
        else:
            # Select the action with the highest Q-value
            q_values = self.q_table[state]
            max_q_value = max(q_values)
            actions_with_max_q_value = [i for i in range(len(q_values)) if q_values[i] == max_q_value]
            action = random.choice(actions_with_max_q_value)
        return action

    # Function to update the Q-learning table based on the reward
    def update_q_table(self, state, action, reward, next_state):
        old_q_value = self.q_table[state][action]
        next_max_q_value = max(self.q_table[next_state])
        new_q_value = old_q_value + self.alpha * (reward + self.gamma * next_max_q_value - old_q_value)
        self.q_table[state][action] = new_q_value

    # Function to update the RED parameters based on the queue size and the queue threshold
    def update_red_parameters(self):
        global DROP_PROBABILITY
        if self.queue_size > MAX_QUEUE_SIZE:
            self.queue_threshold -= 1
        else:
            self.queue_threshold += 1
        if self.queue_threshold < 1:
            self.queue_threshold = 1
        if self.queue_threshold > 100:
            self.queue_threshold = 100
        drop_probability = self.max_drop_probability * (self.queue_size - MAX_QUEUE_SIZE) / MAX_QUEUE_SIZE
        if drop_probability < self.min_drop_probability:
            drop_probability = self.min_drop_probability
        if drop_probability > self.max_drop_probability:
            drop_probability = self.max_drop_probability
        DROP_PROBABILITY = drop_probability

    # Function to generate a random MAC address
    def random_mac(self):
        mac = [0x00, 0x16, 0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff)]
        return ':'.join(map(lambda x: "%02x" % x, mac))

