from flask import Flask  
import mysql.connector
import jsonpickle
from flask_cors import CORS
import json
import networkx as nx
import mysql.connector

from sql import sql
from reinf import monte_carlo_rl

app = Flask(__name__)  
CORS(app)
 
@app.route('/')
def home():  
    return "hello, this is our first flask website";  

@app.route('/get_switch_node')
def get_switch_node():
    switch = sql.get_all_switches()
    res = jsonpickle.encode(switch)
    # print(res)
    return res

@app.route('/get_switch_link')
def get_switch_link():
    link = sql.get_all_link()
    res = jsonpickle.encode(link)
    # print(str(res))
    print(res)
    return res
  

@app.route('/get_host')
def get_host():
    h = sql.get_host_table()
    res = {}

    id = 1

    for i in h:
        res.setdefault(id,{})
        res[id]['mac_address'] = i[0]
        res[id]['ip_address'] = i[1]
        res[id]['connected_to'] = i[2]
        res[id]['port'] = i[3]
        id = id + 1
    # print(str(res))
    res = json.dumps(res)
    return res

@app.route('/get_bot')
def get_bot():
    h = sql.get_bot_data()
    res = {}

    id = 1

    for i in h:
        res.setdefault(id,{})
        res[id]['mac_address'] = i[0]
        res[id]['ip_address'] = i[1]
        id = id + 1
    # print(str(res))
    res = json.dumps(res)
    return res

@app.route('/get_path')
def get_path():
    link = []
    switch = []
    host = []
    G = nx.DiGraph()
    arr = []
    
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
            G.add_edge(str(i[1]),str(i[0]))
        
        for i in host:
            G.add_edge(str(i[0]),str(i[1]))
            G.add_edge(str(i[1]),str(i[0]))

        id = 1

        print(host)
        for i in host:
            for j in host:
                if i[0] != j[0]:
                    d = dict()
                    path = []
                    d['key'] = id
                    d['src'] = str(i[0])
                    d['dst'] = str(j[0])
                    try:
                        # print(str(i[0]) + " -> " + str(j[0]))
                        path = nx.shortest_path(G,str(i[0]),str(j[0]))
                        # print(path)

                        d['path'] = path
                        if d not in arr:
                            arr.append(d)
                            id = id + 1

                    except nx.NetworkXNoPath:
                        path = []
                        d['path'] = path

                    except nx.NetworkXError:
                        path=[]
                        d['path'] = path
    finally:
        if mydb.is_connected():
            mycursor.close()
            mydb.close()
    return json.dumps(arr)

@app.route('/traffic_flow_data')
def get_traffic_flow_data():
    data = sql.traffic_data()
    link = []
    switch = []
    host = []
    G = nx.DiGraph()
    result = []

    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="password",
            database="SDN",
            auth_plugin='mysql_native_password'
            )
        mycursor = mydb.cursor()
        s = "SELECT mac_address,switch_id FROM HOST_TABLE;"
        mycursor.execute(s)
        res = mycursor.fetchall()
        host = res

        s = "SELECT switch_id FROM SWITCH_TABLE;"
        mycursor.execute(s)
        s = mycursor.fetchall()
        
        for i in s:
            switch.append(i[0])
        
        s = "SELECT node,connected_to FROM GRAPH_LINK_TABLE;"
        mycursor.execute(s)
        link = mycursor.fetchall()

        for i in host:
            G.add_node(str(i[0]),type='host')

        for i in switch:
            if i[0] not in G:
                G.add_node(str(i[0]),type='switch')
        
        for i in link:
            G.add_edge(str(i[0]),str(i[1]))
            G.add_edge(str(i[1]),str(i[0]))
        
        for i in host:
            G.add_edge(str(i[0]),str(i[1]))
            G.add_edge(str(i[1]),str(i[0]))

        id = 1
        for i in data:
            d = dict()
            d["key"] = id
            d["src_mac"] = i[0]
            d["src_ip"] = i[1]
            d["dst_mac"] = i[2]
            d["dst_ip"] = i[3]
            d["pkt_type"] = i[4]
            d["pkt_size"] = i[5]
            try:
                path = nx.shortest_path(G,str(i[0]),str(i[2]))
                d['path'] = path
            except nx.NetworkXNoPath:
                path = []
                d['path'] = path

            except nx.NetworkXError:
                path=[]
                d['path'] = path

            result.append(d)
            id = id+1
 
    finally:
        if mydb.is_connected():
            mycursor.close()
            mydb.close()


    return json.dumps(result)

@app.route('/get_link_data')
def get_link_data():
    link = sql.link_data()
    res = {}

    id = 1
    # print(link)
    for i in link:
        res.setdefault(id,{})
        res[id]['src_node'] = i[0]
        res[id]['src_port'] = i[1]
        res[id]['dst_node'] = i[2]
        res[id]['dst_port'] = i[3]
        id = id + 1

    res = json.dumps(res)

    return res




@app.route('/truncate')
def truncate():
    sql.truncate_table()

    return True



if __name__ =='__main__':  
    app.run(debug = True)  