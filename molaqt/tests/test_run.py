# test of Run widget
import sys
import os
from unittest import TestCase

from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt

import mola.dataimport as di
import mola.dataview as dv
import mola.build as mb

import molaqt.run as mr
import molaqt.utils as mqu

app = QApplication(sys.argv)


class ModelRunTest(TestCase):
    def test_model_run(self):

        setting = mqu.system_settings(testing=True)
        config_path = setting['config_path'].joinpath('Lemon_Toy_Model.json')
        config = mb.get_config(config_path)
        instance = mb.build_instance(config)

        # get lookups from db
        conn = di.get_sqlite_connection()
        lookup = dv.LookupTables(conn)

        # setup a model run
        model_run = mr.ModelRun(lookup)
        model_run.concrete_model = instance
        model_run.resize(800, 600)
        model_run.show()

        # run the model
        QTest.mouseClick(model_run.run_button, Qt.LeftButton)

        # go through each variable and click on it
        model_run.run_tree.expandAll()
        variables = model_run.run_tree.topLevelItem(0)
        for c in range(variables.childCount()):
            v = variables.child(c)
            print(v.text(0))
            rect = model_run.run_tree.visualItemRect(v)
            QTest.mouseClick(model_run.run_tree.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()

        self.assertIsInstance(model_run, mr.ModelRun)

