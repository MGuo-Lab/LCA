import os
import sys
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

import mola.dataimport as di
import molaqt.dbview as mdb

app = QApplication(sys.argv)


class TestDbView(TestCase):

    def test_init(self):
        db_view = mdb.DbView(di.get_default_db_file())

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(db_view, mdb.DbView)
