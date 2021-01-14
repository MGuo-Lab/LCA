import json
import os
import sys
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

import mola.dataimport as di
import mola.dataview as dv
import mola.specification5 as ms
import molaqt.utils as mqu
import molaqt.widgets as mw


app = QApplication(sys.argv)
setting = mqu.system_settings(testing=True)
config_path = setting['config_path'].joinpath('Orange_Toy_Model.json')

# get lookups from db
conn = di.get_sqlite_connection()
lookup = dv.LookupTables(conn)

# load test configuration file
with open(str(config_path)) as jf:
    model_config = json.load(jf)


class ProcessFlows(TestCase):

    def test_process_flows_editor(self):
        spec = ms.ScheduleSpecification()
        process_flow_editor = mw.ProcessFlow(model_config['sets'], model_config['parameters'], spec, lookup, conn)
        process_flow_editor.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(process_flow_editor, mw.ProcessFlow)

