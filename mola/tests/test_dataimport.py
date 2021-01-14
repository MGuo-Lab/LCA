# unit tests for dataimport module
from unittest import TestCase
import mola.dataimport as di
import sqlite3
import tempfile


class DataImport(TestCase):
    json_zip_filename = "../resources/db/json/Juice_Toy_Model.zip"

    def test_json_to_sqlite(self):
        tfn = tempfile.mktemp()
        fn = di.json_to_sqlite(self.json_zip_filename, tfn)
        self.assertEqual(len(fn), 67)

    def test_get_json_zip(self):
        j = di.get_json_zip(self.json_zip_filename)
        self.assertEqual(j['meta.info']['client'], 'openLCA 1.10.2')

    def test_get_derby(self):
        conn = di.get_jdbc_connection("Z:/work/code/Python/LCA/mola/resources/db/derby/juice_empty",
                                      "Z:/share/db-derby-10.15.1.3-bin/lib/derby.jar")
        df_dict = di.get_derby(conn, table_name=[["APP", "TBL_PROCESSES"]])
        conn.close()
        self.assertEqual(len(df_dict), 1)