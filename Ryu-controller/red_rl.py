import random
from tokenBucket import TokenBucket

# Define the maximum queue size and the initial RED parameters
MAX_QUEUE_SIZE = 100
MIN_THRESHOLD = 10
MAX_THRESHOLD = 90
DROP_PROBABILITY = 0.0


class RED_Rl(object):

    def __init__(self):
        # self.mac_to_port = {}
        # self.datapaths = {}
        self.queue_size = 0
        self.queue_threshold = MAX_THRESHOLD
        self.q_table = {}
        self.alpha = 0.1
        self.gamma = 0.9
        self.epsilon = 0.1
        self.action_space = [0,1]
        self.observation_space = [(0, 0), (0, 1), (1, 0), (1, 1)]

        self.max_drop_probability = 0.01
        self.min_drop_probability = 0.9

    def update_q_table(self, state, action, reward, next_state):
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0]
        q_value = self.q_table[state][action]
        max_q_value = max(self.q_table[next_state])
        new_q_value = (1 - self.alpha) * q_value + self.alpha * (reward + self.gamma * max_q_value)
        self.q_table[state][action] = new_q_value

    def select_action(self, state):
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0]
        if random.uniform(0, 1) < self.epsilon:
            action = random.choice(self.action_space)
        else:
            action = self.q_table[state].index(max(self.q_table[state]))
        return action

    def update_red_parameters(self):
        avg_queue_length = float(self.queue_size) / float(MAX_QUEUE_SIZE)
        drop_probability = (avg_queue_length - float(self.queue_threshold) / 100.0) / 2.0
        drop_probability = max(0.0, min(drop_probability, 1.0))
        global DROP_PROBABILITY
        DROP_PROBABILITY = drop_probability

    # Function to select an action based on the current state and the Q-learning table
    def select_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            # Select a random action
            action = random.choice(self.action_space)
        else:
            # Select the action with the highest Q-value
            if state not in self.q_table:
                self.q_table[state] = [0.0, 0.0]
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

