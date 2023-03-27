import networkx as nx
import mysql.connector
import networkx as nx
import random
import resource
resource.setrlimit(resource.RLIMIT_DATA, (2**32,-1))


# Define the Monte Carlo Reinforcement Learning algorithm
def monte_carlo_rl(graph, source, dest, num_episodes, epsilon, cutoff):
    # Initialize the state-action value function Q(s,a)
    q_values = {}
    for node in graph.nodes():
        for neighbor in graph.neighbors(node):
            q_values[(node, neighbor)] = 0.0

    # Initialize the policy to be a random policy
    policy = {}
    for node in graph.nodes():
        policy[node] = random.choice(list(graph.neighbors(node)))

    # Repeat for a fixed number of episodes
    for i in range(num_episodes):
        # Choose a starting node and initialize the episode
        current_node = source
        episode = []
        step = 0

        # Follow the current policy to traverse the graph and accumulate rewards
        while current_node != dest and step < cutoff:
            next_node = policy[current_node]
            reward = -1.0
            episode.append((current_node, next_node, reward))
            current_node = next_node
            step += 1

        # Update the state-action value function Q(s,a) using the Monte Carlo update rule
        returns = {}
        for s, a, r in episode:
            state_action = (s, a)
            if state_action not in returns:
                returns[state_action] = 0.0
            returns[state_action] += r

        for state_action in returns:
            q_values[state_action] += (returns[state_action] - q_values[state_action]) / (i + 1)

        # Update the policy to be an epsilon-greedy policy based on the current state-action value function Q(s,a)
        for node in graph.nodes():
            best_action = max(graph.neighbors(node), key=lambda neighbor: q_values[(node, neighbor)])
            for neighbor in graph.neighbors(node):
                if neighbor == best_action:
                    policy[node] = neighbor
                else:
                    policy[node] = random.choice(list(graph.neighbors(node))) if random.random() < epsilon else best_action

    # Use the final state-action value function Q(s,a) to find the shortest path
    path = [source]
    current_node = source
    while current_node != dest:
        neighbors = list(graph.neighbors(current_node))
        q_values_neighbors = [q_values[(current_node, neighbor)] for neighbor in neighbors]
        next_node = neighbors[q_values_neighbors.index(max(q_values_neighbors))]
        path.append(next_node)
        current_node = next_node

    return path

def get_path():
    link = []
    switch = []
    host = []
    G = nx.DiGraph()
    result = {}
    
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="password",
            database="SDN",
            auth_plugin='mysql_native_password'
            )
        mycursor = mydb.cursor()
        sql = "SELECT mac_address,switch_id FROM HOST_TABLE;"
        mycursor.execute(sql)
        res = mycursor.fetchall()
        host = res

        sql = "SELECT switch_id FROM SWITCH_TABLE;"
        mycursor.execute(sql)
        s = mycursor.fetchall()
        
        for i in s:
            switch.append(i[0])
        
        sql = "SELECT node,connected_to FROM GRAPH_LINK_TABLE;"
        mycursor.execute(sql)
        link = mycursor.fetchall()

        for i in host:
            G.add_node(str(i[0]),type='host')

        for i in switch:
            if i[0] not in G:
                G.add_node(str(i[0]),type='switch')
        
        for i in link:
            G.add_edge(str(i[0]),str(i[1]))
        
        for i in host:
            G.add_edge(str(i[0]),str(i[1]))

        for i in host:
            for j in host:
                if i != j:
                    try:
                        path = nx.shortest_path(G,str(i[0]),str(j[0]))
                        print("from " + str(i) + "to " + str(j) + " -> " +str(path))
                    except nx.NetworkXNoPath:
                        print("[+]\tNo path found between %s - %s",i[0],j[0])
                        # return None
                    except nx.NetworkXError:
                        print("Network Error")
                        # return None
    finally:
        if mydb.is_connected():
            mycursor.close()
            mydb.close()

    return result

s = get_path()


# link = []
# switch = []
# host = []
# G = nx.DiGraph()
 
# try:
#     mydb = mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="password",
#         database="SDN",
#         auth_plugin='mysql_native_password'
#         )
#     mycursor = mydb.cursor()
#     sql = "SELECT mac_address,connected_to_switch_id FROM HOST_TABLE;"
#     mycursor.execute(sql)
#     res = mycursor.fetchall()
#     host = res

#     sql = "SELECT switch_id FROM SWITCH_TABLE;"
#     mycursor.execute(sql)
#     s = mycursor.fetchall()
    
#     for i in s:
#         switch.append(i[0])
    
#     sql = "SELECT node,connected_to FROM GRAPH_LINK_TABLE;"
#     mycursor.execute(sql)
#     link = mycursor.fetchall()

#     for i in host:
#         G.add_node(i[0],type='host')

#     for i in switch:
#         if i[0] not in G:
#             G.add_node(i[0],type='switch')
    
#     for i in link:
#         G.add_edge(i[0],i[1])
    
#     for i in host:
#         G.add_edge(i[0],i[1])

#     pos = nx.spring_layout(G,k=1, iterations=20)
#     nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=1000, edge_color='gray',width=2)
#     nx.draw_networkx_labels(G, pos)
#     plt.title("Network topologies from RYU Controller") 
#     # plt.savefig('/home/hp/Desktop/fyp/fyp-implem/result/Images/network-topology/" + fig ".png")
#     plt.show()
    

# finally:
#     if mydb.is_connected():
#         mycursor.close()
#         mydb.close()


        