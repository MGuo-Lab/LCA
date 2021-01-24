"""
Import and export openLCA Derby databases
"""
from pathlib import Path
import jaydebeapi as jdbc
import pandas as pd
import numpy as np
import json
import zipfile
import sqlite3
import os
import gc
import time
import platform


def get_default_db_file():
    if platform.system() == 'Windows':
        default_db_file = 'C:/data/openlca/sqlite/system/CSV_juice_ecoinvent_36_apos_lci_20200206_20201029-102818.sqlite'
    else:
        default_db_file = '/mnt/disk1/data/openlca/sqlite/system/CSV_juice_ecoinvent_36_apos_lci_20200206_20201029-102818.sqlite'

    return default_db_file


def clob_to_string(x):
    """ convert java clobs to strings"""
    if type(x) is type(None):
        y = ""
    else:
        clob_length = int(x.length())
        y = x.getSubString(1, clob_length)
    return y


def get_jdbc_connection(db_dir_name, derby_jar):
    """ Get JDBC connection to an uncompressed Derby database.
        Needs an installed JVM.
    :param db_dir_name: full path to Derby folder
    :param derby_jar: full path of Derby driver jar
    :return: connection object or None
    """

    conn = None
    try:
        conn = jdbc.connect("org.apache.derby.iapi.jdbc.AutoloadedDriver",
                            "jdbc:derby:" + str(db_dir_name),
                            {'user': "", 'password': ""}, str(derby_jar))
    except sqlite3.Error as e:
        print(e)

    return conn


LCA_table = [
    ["APP", "TBL_LOCATIONS"],
    ["APP", "TBL_PROCESSES"],
    ["APP", "TBL_FLOWS"]
    # ["APP", "TBL_EXCHANGES"]
]


def derby_to_csv(db_conn, db_folder, separate_lob=False):
    """
    Uses the SYSCS_UTIL.SYSCS_EXPORT_TABLE method to export to headerless CSV files.
    :param db_conn JDBC connection
    :param db_folder full path to Derby database folder
    :return: path to folder containing CSV files
    """

    csv_path = str(db_folder) + '_' + str(time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(csv_path)

    table_name = get_derby_tables(db_conn)

    # export each table to csv
    curs = db_conn.cursor()

    for tbl in table_name:
        print("Exporting", tbl, "to csv")
        if separate_lob:
            call_str = "CALL SYSCS_UTIL.SYSCS_EXPORT_TABLE_LOBS_TO_EXTFILE (%s,%s,%s,%s,%s,%s,%s)" % \
                       (
                           'null',
                           "'" + tbl + "'",
                           "'" + csv_path + "/" + tbl + ".csv'",
                           'null',
                           'null',
                           "'UTF-8'",
                           "'" + csv_path + "/" + tbl + ".lob'")
        else:
            call_str = "CALL SYSCS_UTIL.SYSCS_EXPORT_TABLE (%s,%s,%s,%s,%s,%s)" % \
                       (
                           'null',
                           "'" + tbl + "'",
                           "'" + csv_path + "/" + tbl + ".csv'",
                           'null',
                           'null',
                           "'UTF-8'")
        print(call_str)
        curs.execute(call_str)
    return Path(csv_path)


def csv_to_sqlite(csv_folder, db_file, table_cols, method=None, chunk_size=1000000):
    """
    Get openLCA CSV data in a folder and convert to a sqlite database.

    :param csv_folder folder containing CSV files for each table
    :param db_file: full path to sqlite db
    :param table_cols dictionary of table column names
    :param method argument passed to DataFrame.to_sql
    :param chunk_size: chunk size for pandas
    :return: Path of sqlite db
    """

    # get all the CSVs in folder
    csv_name = [f for f in os.listdir(str(csv_folder)) if f.endswith('.csv')]

    # connect to sqlite database
    if os.path.exists(str(db_file)):
        os.remove(str(db_file))
    sqlite_conn = get_sqlite_connection(str(db_file))

    # write each CSV file to sqlite db
    for tbl in csv_name:

        csv_file = str(csv_folder) + '/' + tbl
        if os.path.getsize(csv_file) > 0:
            print("Importing file", tbl)
            tbl_name = os.path.splitext(tbl)[0]
            chunk_num = 0
            for chunk in pd.read_csv(csv_file, chunksize=chunk_size, header=None, index_col=None, low_memory=False):
                chunk.columns = table_cols[tbl_name]
                chunk.to_sql(tbl_name, sqlite_conn, if_exists='append', index=False, method=method)
                print('Exported chunk', chunk_num)
                chunk_num += 1
                del chunk
                gc.collect()

    return db_file


def derby_to_sqlite(db, derby_input_folder, csv_output_folder, sqlite_output_folder,
                    derby_driver_path='C:/share/db-derby-10.15.1.3-bin/lib/derby.jar', version=None):
    """
    Bulk export from derby to CSV and then use pandas to write the CSVs to a sqlite database
    :return: full path to sqlite database
    """

    # set up paths
    db_folder = csv_output_folder + '/' + db
    csv_folder = db_folder + "_" + version
    sqlite_file = csv_output_folder + '/' + 'CSV_' + db + "_" + version + '.sqlite'

    # convert Derby database to CSV
    conn = get_jdbc_connection(derby_input_folder + '/' + db, derby_driver_path)
    table_names = get_derby_tables(conn)
    table_cols = get_derby_table_column_names(conn, table_names)
    csv_folder = derby_to_csv(conn, db_folder, separate_lob=True)
    conn.close()

    # generate sqlite db
    output_db = csv_to_sqlite(csv_folder, sqlite_file, table_cols, chunk_size=1000000)

    return output_db


# def csv_to_sqlite_dask(csv_folder, db_file, table_cols):
#     """
#     Get openLCA CSV data in a folder and convert to a sqlite database.
#
#     :param csv_folder folder containing CSV files for each table
#     :param db_file: file name for sqlite db
#     :param table_cols dictionary of table column names
#     :return: file path of sqlite db
#     """
#
#     # get all the CSVs in folder
#     csv_name = [f for f in os.listdir(csv_folder) if f.endswith('.csv')]
#
#     # connect to sqlite database
#     if os.path.exists(db_file):
#         os.remove(db_file)
#     #sqlite_uri = create_engine('sqlite:///%s' % db_file)
#
#     # write each CSV file to sqlite db
#     for tbl in csv_name:
#
#         csv_file = csv_folder + '/' + tbl
#         if os.path.getsize(csv_file) > 0:
#             print("Importing file", tbl)
#             tbl_name = os.path.splitext(tbl)[0]
#             ddf = dask.dataframe.read_csv(csv_file, header=None)
#             ddf.columns = table_cols[tbl_name]
#             # pbar = ProgressBar()
#             # pbar.register()
#             col_types = ddf.dtypes.to_dict()
#
#             i = 0
#             for i in range(ddf.npartitions):
#                 partition = ddf.get_partition(i)
#                 partition.to_sql(tbl_name, uri='sqlite:///%s' % db_file, dtype=col_types, if_exists='append', index=False)
#                 i += 1
#
#             print("Exported ", tbl_name)
#
#     return db_file


def get_derby_table_column_names(db_conn, table_name):
    """
    Get a dictionary of table column names

    :param db_conn: JDBC database connection
    :param table_name: list of table names
    :return: dictionary of column names keyed by table name
    """

    # construct query string
    tbl_str = ','.join("'{0}'".format(t) for t in table_name if len(t) > 0)
    curs = db_conn.cursor()
    ex_str = """
    select * 
    FROM sys.systables t, sys.syscolumns 
    WHERE TABLEID = REFERENCEID and tablename IN (%s)
    """ % tbl_str
    print(ex_str)

    # fetch meta data as named DataFrame
    curs.execute(ex_str)
    col_names = [curs._meta.getColumnName(i) for i in range(1, curs._meta.getColumnCount() + 1)]
    f = curs.fetchall()
    dfr = pd.DataFrame(f, columns=col_names)

    # split by columns by TABLENAME
    x = {g: dfr['COLUMNNAME'].to_list() for (g, dfr) in dfr.groupby(dfr['TABLENAME'])}

    return x


def get_derby_tables(db_conn):
    """
    Get table names from a Derby database.
    :param db_conn: Derby database connection
    :return: list of tables
    """
    curs = db_conn.cursor()
    ex_str = """
    SELECT (SELECT SCHEMANAME  
    FROM SYS.SYSSCHEMAS  
    WHERE SYS.SYSTABLES.SCHEMAID = SYS.SYSSCHEMAS.SCHEMAID) 
    AS SCHEMANAME, TABLENAME 
    FROM SYS.SYSTABLES WHERE TABLETYPE='T'
    """
    curs.execute(ex_str)
    tbl = [t[1] for t in curs.fetchall() if t[1].startswith('TBL_')]
    return tbl


def get_derby(db_conn, table_name=None, chunk_size=10000):
    """
    Get openLCA data from an uncompressed Derby directory. Can only load a description with small tables because
    of memory issues with jpype.

    :param db_conn: JDBC database connection
    :param table_name: list of [scheme, table]
    :param chunk_size: chunk size for pandas
    :return: dictionary of Pandas dataframes for each table_name
    """

    curs = db_conn.cursor()

    if table_name is None:
        table_name = get_derby_tables(db_conn)

    df_dict = {}
    for (schema, tbl) in table_name:
        # get the table content
        sql_str = "SELECT * from " + schema + "." + tbl
        print(sql_str)
        l = []
        chunk_num = 0
        for chunk in pd.read_sql(sql_str, db_conn, chunksize=chunk_size):
            for i in chunk.dtypes.to_dict().items():
                if i[1] == np.dtype('object'):
                    chunk[i[0]] = chunk[i[0]].astype(str)

            print("Processed chunk", chunk_num)
            chunk_num += 1
            l.append(chunk)

        df_dict[schema + "." + tbl] = None if len(l) == 0 else pd.concat(l, ignore_index=True)

    return df_dict


LCA_cols_to_select = {
    'TBL_EXCHANGES': 'F_FLOW AS ID, RESULTING_AMOUNT_VALUE, F_UNIT'
}


def derby_to_sqlite(db_conn, db_file, table_name=LCA_table, select_cols=LCA_cols_to_select, chunk_size=10000):
    """ Get openLCA data from an uncompressed Derby directory and convert to a sqlite database.

        Can only load a character description with small tables because of memory issues with jpype.
        In TBL_EXCHANGES the description clob seems to be a point to another table so converting to character causes
        Java to run out of memory.

    :param db_conn: JDBC database connection
    :param db_file: file name for sqlite db
    :param table_name: list of [scheme, table]
    :param chunk_size: chunk size for pandas
    :return: file path of sqlite db
    """

    # get all the tables if None specified
    if table_name is None:
        table_name = get_derby_tables(db_conn)

    # connect to sqlite database
    if os.path.exists(db_file):
        os.remove(db_file)
    sqlite_conn = get_sqlite_connection(db_file)

    # write each Derby table to sqlite db
    for tbl in table_name:

        print("Importing table", tbl)

        # get the table content
        chunk_num = 0
        if tbl in select_cols:
            select_str = 'SELECT ' + select_cols[tbl] + ' FROM ' + 'app' + '.' + tbl
        else:
            select_str = 'SELECT * FROM ' + 'app' + '.' + tbl

        for chunk in pd.read_sql(select_str, db_conn, chunksize=chunk_size, index_col=None):

            for i in chunk.dtypes.to_dict().items():
                if i[1] == np.dtype('object'):
                    chunk[i[0]] = chunk[i[0]].astype(str)

            chunk.to_sql(tbl, sqlite_conn, if_exists='append')
            print('Exported chunk', chunk_num)
            chunk_num += 1
            del chunk
            gc.collect()

    return db_file


def get_json_zip(zip_filename):
    """ Get json files in a JSON-LD zip file
    :param zip_filename:
    :return: dictionary of json files
    """

    # get the file names in the zip
    zip_file = zipfile.ZipFile(zip_filename, 'r')
    name_list = zip_file.namelist()

    # build dictionary
    print("Loading", len(name_list), "json files in", zip_filename)
    json_dict = {}
    for name in name_list:
        raw = zip_file.read(name)
        if len(raw) > 0:
            json_dict[name] = json.loads(raw)

    return json_dict


def json_to_custom(zip_filename, db_file_base, limit=None):
    """ Get json files in a JSON-LD zip file and store customised information in a sqlite database.
    :param zip_filename:
    :param db_file_base:
    :param limit: limit the number of processes to export
    :return: file path of time-stamped sqlite db
    """

    # get the file names in the zip
    zip_file = zipfile.ZipFile(zip_filename, 'r')
    name_list = zip_file.namelist()
    print("Loading", len(name_list), "json files in", zip_filename)

    # connect to sqlite database
    if os.path.exists(db_file_base):
        os.remove(db_file_base)
    db_file = db_file_base + '_' + str(time.strftime("%Y%m%d-%H%M%S")) + '.sqlite'
    conn = get_sqlite_connection(db_file)

    # find just the JSON files
    json_file_list = []
    for name in name_list:
        tf = name.split("/")
        if len(tf) > 1 and len(tf[1]) > 0:
            json_file_list.append(tf)

    # limit processes if flag set
    if limit is not None:
        new_file_list = []
        p_count = 0
        for f in json_file_list:
            if f[0] == "processes" and p_count < limit:
                new_file_list.append(f)
                p_count += 1
            elif f[0] != "processes":
                new_file_list.append(f)

        json_file_list = new_file_list

    print("Populating tables ...")
    file_num = 1
    for f in json_file_list:

        # insert exchanges into dedicated table
        if f[0] == "processes":
            j = json.loads(zip_file.read('/'.join(f)))
            ex_dfr = pd.json_normalize(j['exchanges'], max_level=1)  # maybe use flatten here
            ex_dfr.insert(0, 'id', j['@id'])
            out_dfr = ex_dfr[['id', 'input', 'amount']]
            out_dfr.to_sql(f[0], conn, if_exists='append')

        work_done = file_num / len(json_file_list)
        print("\rProgress: [{0:50s}] {1:.1f}%".format('#' * int(work_done * 50), work_done * 100),
              end="", flush=True)
        file_num += 1

    conn.commit()
    conn.close()
    print()
    return db_file


def json_to_sqlite(zip_filename, db_file_base, limit=None):
    """ Get json files in a JSON-LD zip file and store them in a sqlite database.
    :param zip_filename:
    :param db_file_base:
    :param limit: limit the number of processes to export
    :return: file path of time-stamped sqlite db
    """

    # get the file names in the zip
    zip_file = zipfile.ZipFile(zip_filename, 'r')
    name_list = zip_file.namelist()
    print("Loading", len(name_list), "json files in", zip_filename)

    # connect to sqlite database
    if os.path.exists(db_file_base):
        os.remove(db_file_base)
    db_file = db_file_base + '_' + str(time.strftime("%Y%m%d-%H%M%S")) + '.sqlite'
    conn = get_sqlite_connection(db_file)

    # find just the JSON files
    json_file_list = []
    for name in name_list:
        tf = name.split("/")
        if len(tf) > 1 and len(tf[1]) > 0:
            json_file_list.append(tf)

    # create the tables from unique directory names
    c = conn.cursor()
    tbl_list = set([j[0] for j in json_file_list])
    for tbl in tbl_list:
        print("Creating table", tbl)
        sql_stmt = "CREATE TABLE IF NOT EXISTS %s (data json)" % tbl
        c.execute(sql_stmt)
    conn.commit()

    # create dedicated table
    sql_stmt = "CREATE TABLE IF NOT EXISTS process_grid (id text, flowid text, amount real)"
    c.execute(sql_stmt)
    conn.commit()

    # limit processes if flag set
    if limit is not None:
        new_file_list = []
        p_count = 0
        for f in json_file_list:
            if f[0] == "processes" and p_count < limit:
                new_file_list.append(f)
                p_count += 1
            elif f[0] != "processes":
                new_file_list.append(f)

        json_file_list = new_file_list

    # write each json file to db
    print("Populating tables ...")
    file_num = 1
    for f in json_file_list:
        j = json.loads(zip_file.read('/'.join(f)))

        # insert exchanges into dedicated table
        if f[0] == "processes":
            sql_stmt = "insert into process_grid values (?, ?, ?)"
            c.execute(sql_stmt, [json.dumps(j), 0, 0])

        # insert json chunk into table
        sql_stmt = "insert into %s values (?)" % f[0]
        c.execute(sql_stmt, [json.dumps(j)])

        work_done = file_num / len(json_file_list)
        print("\rProgress: [{0:50s}] {1:.1f}%".format('#' * int(work_done * 50), work_done * 100),
              end="", flush=True)
        file_num += 1

    conn.commit()
    conn.close()
    print()
    return db_file

    # def chunker(seq, size):
    #     return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def get_sqlite_connection(db_file=get_default_db_file()):
    """
    Get a database connection to the SQLite database.

    :param db_file: full path to database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(str(db_file))
    except sqlite3.Error as e:
        print(e, db_file)

    return conn


def create_json_indices(db_file):
    conn = get_sqlite_connection(db_file)
    c = conn.cursor()

    sql_stmt = """
    CREATE INDEX IF NOT EXISTS processes_name ON processes ( json_extract(data, '$.name') COLLATE NOCASE )
    """
    c.execute(sql_stmt)

    sql_stmt = """
    CREATE INDEX IF NOT EXISTS flows_name ON flows ( json_extract(data, '$.name') COLLATE NOCASE )
    """
    c.execute(sql_stmt)
    conn.commit()

    conn.close()


def create_csv_indices(db_file):
    """
    Create indices on tables in a sqlite database created from CSVs exported from Derby
    :param db_file: database file
    :return: None
    """
    print("Building indices on", db_file)
    conn = get_sqlite_connection(db_file)
    c = conn.cursor()

    sql_stmt = """
    CREATE UNIQUE INDEX IF NOT EXISTS TBL_EXCHANGES_ID ON TBL_EXCHANGES(ID)
    """
    c.execute(sql_stmt)
    sql_stmt = """
    CREATE INDEX IF NOT EXISTS TBL_FLOWS_ID ON TBL_FLOWS(ID)
    """
    c.execute(sql_stmt)
    sql_stmt = """
    CREATE INDEX IF NOT EXISTS TBL_EXCHANGES_F_FLOW ON TBL_EXCHANGES(F_FLOW)
    """
    c.execute(sql_stmt)
    sql_stmt = """
    CREATE INDEX IF NOT EXISTS TBL_EXCHANGES_F_OWNER ON TBL_EXCHANGES(F_OWNER)
    """
    c.execute(sql_stmt)

    conn.commit()
    conn.close()


def bulk_import(input_dir, output_dir, zip_file, import_fn=json_to_custom, limit=None):
    """ Convert a directory of db files using import_fn
    :param input_dir: full path to location of zip folder
    :param output_dir: full path to output folder
    :param zip_file: list of zip file names
    :param import_fn: function to convert zip to output format
    :param limit the number of processes to export
    :return: list of db names
    """

    fn = []
    for z in zip_file:
        db_base_name = os.path.splitext(z)[0]
        input_db = os.path.join(input_dir, z)
        output_db = os.path.join(output_dir, db_base_name)
        print("Importing", input_db, "...")
        fn.append(import_fn(input_db, output_db, limit))
        print("Exported to", output_db)

    return fn
