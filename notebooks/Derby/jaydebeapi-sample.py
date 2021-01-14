import jaydebeapi as jdbc

conn = jdbc.connect("org.apache.derby.jdbc.ClientDriver", "jdbc:derby://address:port/db_name", ["user", "pwd"], "path/to/derbyclient-10.14.2.jar")
curs = conn.cursor()

curs.execute("select ITEM from TABLENAME")
rec = curs.fetchone()[0]

curs.execute("select BLOB from TABLENAME")
rec = curs.fetchone()[0]

curs.close()
conn.close()