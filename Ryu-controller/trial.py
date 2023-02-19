import mysql.connector

try:
    mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="password",
                database="SDN"
                )
    if mydb.is_connected():
        print("CONNECTED TO DATABASE..")
finally:
    if mydb.is_connected():
        mydb.close()