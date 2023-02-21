import networkx as nx
import matplotlib.pyplot as plt
import mysql.connector

link = []
switch = []
host = []
G = nx.DiGraph()

try:
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="SDN"
        )
    mycursor = mydb.cursor()
    sql = "SELECT mac_address,connected_to_switch_id FROM HOST_TABLE;"
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
        G.add_node(i[0],type='host')

    for i in switch:
        if i[0] not in G:
            G.add_node(i[0],type='switch')
    
    for i in link:
        G.add_edge(i[0],i[1])
    
    for i in host:
        G.add_edge(i[0],i[1])

    pos = nx.spring_layout(G,k=1, iterations=20)
    nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=1000, edge_color='gray',width=2)
    nx.draw_networkx_labels(G, pos)
    plt.title("Network topologies from RYU Controller") 
    # plt.savefig('/home/hp/Desktop/fyp/fyp-implem/result/Images/network-topology/" + fig ".png")
    plt.show()
    

finally:
    if mydb.is_connected():
        mycursor.close()
        mydb.close()


        