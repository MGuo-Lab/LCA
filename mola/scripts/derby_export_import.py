# Bulk export from derby to CSV and then use pandas to write the CSVs to a sqlite database
# remove os dependency
import os
from pathlib import Path
import zipfile
import mola.dataimport as di

# configuration
# db = 'ecoinvent_36_apos_lci_20200206'
# db = 'juice_ecoinvent_36_apos_lci_20200206'
db = 'ecoinvent_371_apos_lci_methods_205_20210105'
csv_path = 'C:/data/openlca/CSV/system'
db_folder = csv_path + '/' + db
sqlite_folder = 'C:/data/openlca/sqlite/system'
derby_driver = 'C:/share/db-derby-10.15.1.3-bin/lib/derby.jar'
derby_db_dir = 'C:/Users/Paul/openLCA-data-1.4/databases'

# convert Derby database to CSV
conn = di.get_jdbc_connection(derby_db_dir + '/' + db, derby_driver)
table_names = di.get_derby_tables(conn)
table_cols = di.get_derby_table_column_names(conn, table_names)
csv_folder = di.derby_to_csv(conn, db_folder, separate_lob=True)
conn.close()

# generate sqlite db
#csv_folder = db_folder + "_" + '20201018-181721'
sqlite_file = sqlite_folder + '/' + 'CSV_' + os.path.basename(csv_folder) + '.sqlite'
di.csv_to_sqlite(csv_folder, sqlite_file, table_cols, chunk_size=1000000)
di.create_csv_indices(sqlite_file)

# compress the sqlite file
sqlite_path = Path(sqlite_file)
zipfile.ZipFile(sqlite_path.with_suffix('.zip'), mode='w').write(sqlite_path)
