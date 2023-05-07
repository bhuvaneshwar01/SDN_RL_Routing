import mysql.connector

class sql():
    def __init__(self) -> None:
        pass

    

    def get_all_switches():
        switch = set()
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
            )
            mycursor = mydb.cursor()
            sql = "SELECT switch_id FROM SWITCH_TABLE;"
            mycursor.execute(sql)
            s = mycursor.fetchall()
            sql = "SELECT mac_address FROM HOST_TABLE;"
            mycursor.execute(sql)
            res = mycursor.fetchall()

            for i in s:
                switch.add(i[0])

            for i in res:
                switch.add(i[0])
            
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        return switch
    
    def get_all_link():
        link = set()
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
            )
            mycursor = mydb.cursor()
            sql = "SELECT node,connected_to FROM GRAPH_LINK_TABLE;"
            mycursor.execute(sql)
            s = mycursor.fetchall()
            sql = "SELECT mac_address,switch_id FROM HOST_TABLE;"
            mycursor.execute(sql)
            res = mycursor.fetchall()

            for i in s:
                link.add((i[0], i[1]))
            
            for i in res:
                link.add((i[0],i[1]))
            
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        return link
     
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
            mydb.commit()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

    def get_host_table():
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "SELECT * FROM HOST_TABLE;"
            # val = (ip_address,mac_address)
            mycursor.execute(sql)
            res = mycursor.fetchall()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        return res
    
    def get_host_switch_table():
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "SELECT * FROM SWTCH_HW_TABLE;"
            # val = (ip_address,mac_address)
            mycursor.execute(sql)
            res = mycursor.fetchall()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        return res
    

    def link_data():
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "SELECT * FROM LINK_TABLE;"
            # val = (ip_address,mac_address)
            mycursor.execute(sql)
            res = mycursor.fetchall()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        return res
    
    def traffic_data():
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "SELECT * FROM TRAFFIC_FLOW_TABLE;"
            # val = (ip_address,mac_address)
            mycursor.execute(sql)
            res = mycursor.fetchall()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        return res
    
    def get_bot_data():
        try:
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN",
                auth_plugin='mysql_native_password'
                )
            mycursor = mydb.cursor()
            sql = "SELECT * FROM BOT_TABLE;"
            # val = (ip_address,mac_address)
            mycursor.execute(sql)
            res = mycursor.fetchall()
            # print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
        return res