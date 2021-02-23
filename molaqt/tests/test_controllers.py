# tests for controller widgets
import os
import sys
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

import mola.dataimport as di
import mola.dataview as dv
import molaqt.controllers as mc
import molaqt.utils as mqu

app = QApplication(sys.argv)

# get lookups from db - FIXME mock this using hand-built sqlite db
conn = di.get_sqlite_connection()
lookup = dv.LookupTables(conn)

# json config dicts for testing - the controller ensures defaults used but could replace with build_config
orange_config = mqu.get_config('Orange_Toy_Model.json')[0]
custom_config = mqu.get_config('test_custom_controller.json')[0]


class TestCustomController(TestCase):
    def test_init(self):
        custom_controller = mc.CustomController(custom_config)
        custom_controller.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(custom_controller, mc.CustomController)


class TestStandardController(TestCase):
    def test_init(self):
        standard_controller = mc.StandardController(orange_config)
        standard_controller.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(standard_controller, mc.StandardController)
