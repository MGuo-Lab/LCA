import json
import os
import sys
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

import mola.dataimport as di
import mola.dataview as dv
import molaqt.controllers as mc
import molaqt.utils as mqu


app = QApplication(sys.argv)
setting = mqu.system_settings(testing=True)
config_path = setting['config_path'].joinpath('Orange_Toy_Model.json')

# get lookups from db - FIXME mock this
conn = di.get_sqlite_connection()
lookup = dv.LookupTables(conn)

# load test configuration file
with open(str(config_path)) as jf:
    model_config = json.load(jf)


class TestStandardController(TestCase):
    def test_init(self):
        standard_controller = mc.StandardController(model_config)
        standard_controller.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(standard_controller, mc.StandardController)
