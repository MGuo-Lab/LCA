# Bulk export from derby to CSV and then use pandas to write the CSVs to a sqlite database
from pathlib import Path
import zipfile
import mola.dataimport as di

# configuration
# db = 'ecoinvent_36_apos_lci_20200206'
# db = 'juice_ecoinvent_36_apos_lci_20200206'
# db = 'ecoinvent_371_apos_lci_methods_205_20210105'
db = 'ecoinvent_371_apos_lci_20210105_36_methods'
csv_path = Path('C:/data/openlca/CSV/system')
db_dir = csv_path.joinpath(db)
sqlite_dir = Path('C:/data/openlca/sqlite/system')
derby_driver = Path('C:/share/db-derby-10.15.1.3-bin/lib/derby.jar')
derby_db_dir = Path('C:/Users/Paul/openLCA-data-1.4/databases')
zip_dir = Path('C:/data/openlca/zip')

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
