import jaydebeapi as jdbc
import pandas as pd
 
conn = jdbc.connect("org.apache.derby.iapi.jdbc.AutoloadedDriver", 
                    "jdbc:derby:/mnt/disk1/media/KCL_Supply_Chain_Optimisation/LCA_workshop/ecoinvent_36_apos_unit_20191212",
                    ["", ""], "/mnt/disk1/share/db-derby-10.15.1.3-bin/lib/derby.jar")
curs = conn.cursor()

curs.execute("SELECT * from TBL_PROCESSES")
rec = curs.fetchmany(100)
col_names = [i[0] for i in curs.description]
df = pd.DataFrame(rec, columns = col_names)

curs.close()
conn.close()
df
