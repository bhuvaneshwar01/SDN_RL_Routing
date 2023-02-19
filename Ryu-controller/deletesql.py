import mysql.connector

try:
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="SDN"
        )
    mycursor = mydb.cursor()
    sql = "TRUNCATE HOST_TABLE;"
    mycursor.execute(sql)
    sql = "TRUNCATE LINK_TABLE;"
    mycursor.execute(sql)
    sql = "TRUNCATE SWITCH_TABLE;"
    mycursor.execute(sql)
    print(mycursor.rowcount, "record deleted.")
finally:
    if mydb.is_connected():
        mycursor.close()
        mydb.close()