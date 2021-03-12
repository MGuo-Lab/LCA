# Bulk export from derby to CSV and then use pandas to write the CSVs to a sqlite database
from pathlib import Path
import os
import zipfile
import mola.dataimport as di

# You need to have Java installed on your system for this script to work. OpenLCA should install a copy of Java.
# It needs to be on your path so that the Python package jaydebc can use it.
# I have C:\Program Files\AdoptOpenJDK\jdk-11.0.8.10-hotspot\bin on my path.

# Using openLCA, import the Ecoinvent system LCI database (it contains a methods db) called
# juice_ecoinvent_36_apos_lci_20200206.zolca located at https://app.box.com/folder/133200648503?utm_source=trans.
# Close openLCA.

# To import Ecoinvent 371 import the 36 methods file ecoinvent_36_lcia_methods.zip at box.com and modify the db variable
# below. Newer methods versions seem to use a different db structure and so are not imported correctly by this
# script.

# Start of configuration

# OpenLCA holds databases in the following directory in Windows 10
derby_db_dir = Path('C:/Users/Paul/openLCA-data-1.4/databases')

# The Derby database should be in the following folder in the openLCA database folder.
db = 'juice_ecoinvent_36_apos_lci_20200206'
# db = 'ecoinvent_36_apos_lci_20200206'
# db = 'ecoinvent_371_apos_lci_methods_205_20210105'
# db = 'ecoinvent_371_apos_lci_20210105_36_methods'

# To access the Derby database, download the Derby driver at http://db.apache.org/derby/ to the folder below.
derby_driver = Path('C:/share/db-derby-10.15.1.3-bin/lib/derby.jar')

# The following folder will be created on the filesystem to hold temporary CSV exports from Derby
csv_path = Path('C:/data/openlca/CSV/system')

# The following output folder holds the generated sqlite database. Ensure the folder exists.
sqlite_dir = Path('C:/data/openlca/sqlite/system')

# The sqlite file is zipped into the following folder for import into mola. Ensure the folder exists.
zip_dir = Path('C:/data/openlca/zip')
db_dir = csv_path.joinpath(db)

# End of configuration

# convert Derby database to CSV
conn = di.get_jdbc_connection(derby_db_dir.joinpath(db), derby_driver)
table_names = di.get_derby_tables(conn)
table_cols = di.get_derby_table_column_names(conn, table_names)
csv_output_dir = di.derby_to_csv(conn, db_dir, separate_lob=True)
conn.close()

# generate sqlite db
sqlite_file = sqlite_dir.joinpath('CSV_' + csv_output_dir.name + '.sqlite')
di.csv_to_sqlite(csv_output_dir, sqlite_file, table_cols, chunk_size=1000000)
di.create_csv_indices(sqlite_file)

# compress the sqlite file
zip_file = zip_dir.joinpath(sqlite_file.with_suffix('.zip').name)
zipfile.ZipFile(zip_file, mode='w', compression=zipfile.ZIP_DEFLATED).write(sqlite_file, arcname=sqlite_file.name)
print('Generated', zip_file)
