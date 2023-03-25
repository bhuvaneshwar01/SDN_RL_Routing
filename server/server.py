from flask import Flask  
import mysql.connector
import jsonpickle
from flask_cors import CORS
import json

from sql import sql

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

@app.route('/truncate')
def truncate():
    sql.truncate_table()

    return True

if __name__ =='__main__':  
    app.run(debug = True)  