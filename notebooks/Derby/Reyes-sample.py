""" Derby Class SimpleApp.py
    Add derby.jar to your CLASSPATH
    Ported by: Alfonso Reyes, September 2007

"""
from RSMD import printRSMD, RSMD    # nice methods I downloaded from IBM site
from java.sql import Connection, DriverManager, ResultSet, SQLException, Statement

from java.util import Properties
from java.lang import Class

class SimpleApp:
    def __init__(self):
        # the default framework is embedded
        self.framework = "embedded"
        self.driver = "org.apache.derby.jdbc.EmbeddedDriver"
        self.protocol = "jdbc:derby:"
        self.username = "user1"
        self.password = "user1"

    def go(self):
        # parse the arguments to determine which framework is desired
        #parseArguments(args)
        """   The driver is installed by loading its class.
        In an embedded environment, this will start up Derby, since it is not already running.

        """
        ds = None
        conn = None
        props = Properties()
        props.put("user", self.username)
        props.put("password", self.password)
        print props

        # check for J2ME specification - J2ME must use a DataSource further on */
        javaspec = props.getProperty( "java.specification.name" )

        """
           The connection specifies create=true in the url to cause
           the database to be created. To remove the database,
           remove the directory derbyDB and its contents.
           The directory derbyDB will be created under
           the directory that the system property
           derby.system.home points to, or the current
           directory if derby.system.home is not set.

         """
        Class.forName(self.driver).newInstance()
        print "Loaded the appropriate driver."

        database = "derbyDB5"   # put here the name for your database
        dbStr = self.protocol + database + ";create=true"
        print dbStr
        conn = DriverManager.getConnection(dbStr, props)
        print "Connected to and created database derbyDB"

        conn.setAutoCommit(False)

        """    Creating a statement lets us issue commands against
        the connection.

        """
        s = conn.createStatement()

        #   We create a table, add a few rows, and update one.
        s.execute("create table derbyDB(num int, addr varchar(40))")
        print "Created table derbyDB"
        s.execute("insert into derbyDB values (1956,'Webster St.')")
        print "Inserted 1956 Webster"
        s.execute("insert into derbyDB values (1910,'Union St.')")
        print "Inserted 1910 Union"
        s.execute("insert into derbyDB values (1,'Wandering Oak')")
        print "Inserted 1 Wandering Oak"

        s.execute(
            "update derbyDB set num=180, addr='Grand Ave.' where num=1956")
        print "Updated 1956 Webster to 180 Grand"

        s.execute(
            "update derbyDB set num=300, addr='Lakeshore Ave.' where num=180")
        print "Updated 180 Grand to 300 Lakeshore"

        #  We select the rows and verify the results.
        rs = s.executeQuery("SELECT num, addr FROM derbyDB ORDER BY num")

        print "Verified the rows"
        stmt   = conn.createStatement()
        Query  = 'SELECT * FROM derbyDB'
        rs     = stmt.executeQuery( Query )
        rsmd   = RSMD( rs )
        printRSMD( rsmd, Query )

        rowCount = 0
        while ( rs.next() ) :
            rowCount += 1
            row = ( rs.getInt( 1 ), rs.getString( 2 ) )
            print row

        stmt.close()        # close stmt connection
        s.execute("drop table derbyDB")
        print"Dropped table derbyDB"

        # We release the result and statement resources.
        rs.close()
        s.close()
        print "Closed result set and statements"

        #  We end the transaction and the connection.
        conn.commit()
        conn.close()
        print "Committed transaction and closed connection"

        """   In embedded mode, an application should shut down Derby.
           If the application fails to shut down Derby explicitly,
           the Derby does not perform a checkpoint when the JVM shuts down, which means
           that the next connection will be slower.
           Explicitly shutting down Derby with the URL is preferred.
           This style of shutdown will always throw an "exception".

        """
        gotSQLExc = False
        try:
            DriverManager.getConnection("jdbc:derby:;shutdown=true")
        except SQLException:
            print "Catching exceptions"
            gotSQLExc = True

        if (not gotSQLExc):
            print "Database did not shut down normally"
        else:
            print "Database shut down normally"
        print("SimpleApp finished")

if __name__ == '__main__':
    SimpleApp().go()