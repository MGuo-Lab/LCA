import json
import os
import sys
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

import mola.dataimport as di
import mola.dataview as dv
import molaqt.utils as mqu
import molaqt.widgets as mw

# get lookups from db
app = QApplication(sys.argv)
conn = di.get_sqlite_connection()
lookup = dv.LookupTables(conn)
model_config, spec = mqu.get_config('test_custom_controller.json')


class ProcessFlows(TestCase):

    def test_process_flows_editor(self):
        process_flow_editor = mw.ProcessFlow(model_config['sets'], model_config['parameters'], spec, lookup, conn)
        process_flow_editor.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(process_flow_editor, mw.ProcessFlow)
