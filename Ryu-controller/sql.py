import mysql.connector

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

    def insert_bot_data(mac_addr,ip_addr):
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
            sql = """INSERT INTO BOT_TABLE(mac_address,ip_address) values (%s,%s);"""
            val = (mac_addr,ip_addr)
            mycursor.execute(sql,val)
            mydb.commit()
            print(mycursor.rowcount, "record inserted.")
        finally:
            if mydb.is_connected():
                mycursor.close()
                mydb.close()

# mysql.connector.errors.ProgrammingError: 1064 (42000): You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near '.0.3' at line 1

        