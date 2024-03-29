import mysql.connector
import json
from prettytable import PrettyTable

class sql():
    def insert_host_data(mac_address, switch_id, port_no):
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS HOST_TABLE (mac_address VARCHAR(50),ip_address VARCHAR(50),switch_id VARCHAR(50),port VARCHAR(50));"
            mycursor.execute(sql)
            sql = "INSERT INTO HOST_TABLE(mac_address,switch_id,port) values (%s, %s,%s)"
            val = (str(mac_address),str(switch_id),str(port_no))
            mycursor.execute(sql,val)
            mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        
    def delete_host_data(mac):
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql= "DELETE FROM HOST_TABLE WHERE mac_address = (%s);"
            val = (mac,)
            mycursor.execute(sql,val)
            mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

    def update_mac_ip_host(mac_address,ip_address):
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "UPDATE HOST_TABLE SET ip_address = %s where mac_address = %s"
            val = (ip_address,mac_address)
            mycursor.execute(sql,val)
            mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

    def inserting_traffic_flow(res):
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS TRAFFIC_FLOW_TABLE (src_mac VARCHAR(50),src_ip VARCHAR(50),dst_mac VARCHAR(50),dst_ip VARCHAR(50),pkt_type VARCHAR(50),pkt_len VARCHAR(50),path JSON);"
            mycursor.execute(sql)
            sql = "TRUNCATE TRAFFIC_FLOW_TABLE;"
            mycursor.execute(sql)
            #  = "ALTER TABLE TRAFFIC_FLOW_TABLE ADD UNIQUE INDEX(, name);"


            for i in res:    
                sql = "INSERT IGNORE INTO TRAFFIC_FLOW_TABLE(src_mac,src_ip,dst_mac,dst_ip,pkt_type,pkt_len,path) values (%s,%s, %s,%s,%s, %s,JSON_OBJECT('path',%s))"
                val = (str(i['src_mac']),str(i['src_ip']),str(i['dst_mac']),str(i['dst_ip']),str(i['pkt_type']),str(i['pkt_size']),json.dumps(i['path']))
                mycursor.execute(sql,val)
            mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()


    def truncate_host_table():
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "TRUNCATE HOST_TABLE;"
            # val = (ip_address,mac_address)
            mycursor.execute(sql)
            mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

    def insert_bot_data(ip_addr):
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS BOT_TABLE (mac_address VARCHAR(50),ip_address VARCHAR(50)) ;"
            mycursor.execute(sql)
            sql = "SELECT * FROM BOT_TABLE WHERE ip_address = %s ;" 
            mycursor.execute(sql, (ip_addr,))
            res =  mycursor.fetchall()
            if res:
                return
            sql = "INSERT INTO BOT_TABLE(ip_address) values (%s);"
            val = (ip_addr,)
            mycursor.execute(sql,val)
            mydb.commit()
            print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

    def insert_switch_details(req):
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS SWITCH_DETAILS_TABLE (switch_id VARCHAR(50),(port_no VARCHAR(50)) ;"
            mycursor.execute(sql)
            sql = "SELECT * FROM BOT_TABLE WHERE ip_address = %s ;" 
            mycursor.execute(sql, (ip_addr,))
            res =  mycursor.fetchall()
            if res:
                return
            sql = "INSERT INTO BOT_TABLE(ip_address) values (%s);"
            val = (ip_addr,)
            mycursor.execute(sql,val)
            mydb.commit()
            print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
# mysql.connector.errors.ProgrammingError: 1064 (42000): You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near '.0.3' at line 1

    def insert_hw_swtch(temp_dict):
        # Create the table headers
        # table = PrettyTable(['Switch', 'IP Address', 'Connected Host MAC', 'Switch Port No', 'Switch Port MAC'])

        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql="CREATE TABLE IF NOT EXISTS SWTCH_HW_TABLE (switch VARCHAR(50),ip_address VARCHAR(50),cnttd_to_mac VARCHAR(50),switch_port_no VARCHAR(50),switch_mac VARCHAR(50));"
            mycursor.execute(sql)
            sql = "TRUNCATE SWTCH_HW_TABLE;"
            mycursor.execute(sql)
            #  = "ALTER TABLE TRAFFIC_FLOW_TABLE ADD UNIQUE INDEX(, name);"

            for switch, hosts in temp_dict.items():
                for ip, data in hosts.items():
                    sql = "INSERT IGNORE INTO SWTCH_HW_TABLE(switch,ip_address,cnttd_to_mac,switch_port_no,switch_mac) values (%s,%s, %s,%s,%s)"
                    val = (switch, ip, data['connected_host_mac'], data['sw_port_no'], data['sw_port_mac'])
                    mycursor.execute(sql,val)
                    mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

        # Add the rows to the table
        
                

    def truncate_table():
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "TRUNCATE HOST_TABLE;"
            mycursor.execute(sql)
            sql = "TRUNCATE SWITCH_TABLE;"
            mycursor.execute(sql)
            sql = "TRUNCATE BOT_TABLE;"
            mycursor.execute(sql)
            sql = "TRUNCATE GRAPH_LINK_TABLE;"
            mycursor.execute(sql)
            sql = "TRUNCATE LINK_TABLE;"
            mycursor.execute(sql)
            # sql = "TRUNCATE TRAFFIC_FLOW_TABLE;"
            # mycursor.execute(sql)
            mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
