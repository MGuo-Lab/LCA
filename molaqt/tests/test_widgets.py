import json
import os
import sys
from unittest import TestCase
from pathlib import Path

from PyQt5.QtWidgets import QApplication

import mola.dataimport as di
import mola.dataview as dv
import mola.specification5 as ms
import molaqt.utils as mqu
import molaqt.widgets as mw

app = QApplication(sys.argv)


class Widgets(TestCase):
    # get lookups from db
    conn = di.get_sqlite_connection()
    lookup = dv.LookupTables(conn)

    system_setting = mqu.system_settings(testing=True)
    config_path = system_setting['config_path'].joinpath('Orange_Toy_Model.json')

    # load test configuration file
    with open(str(config_path)) as jf:
        model_config = json.load(jf)

    def test_lookup_widget(self):
        lookup_widget = mw.LookupWidget(self.lookup, 'P_m')

        if 'IGNORE_EXEC' not in os.environ:
            ok = lookup_widget.exec()
            if ok:
                # FIXME simulate lookup table and selecting lookups
                print(lookup_widget.get_elements())
        self.assertIsInstance(lookup_widget, mw.LookupWidget)

    def test_sets_editor(self):
        spec = ms.ScheduleSpecification()
        sets_editor = mw.SetsEditor(self.model_config['sets'], spec, self.lookup)
        sets_editor.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(sets_editor, mw.SetsEditor)

    def test_parameters_editor(self):
        spec = ms.ScheduleSpecification()
        parameters_editor = mw.ParametersEditor(self.model_config['sets'], self.model_config['parameters'], spec,
                                                self.lookup)
        parameters_editor.resize(800, 600)
        parameters_editor.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(parameters_editor, mw.ParametersEditor)

    def test_doc_widget(self):

        doc_path = Path(r'Z:\work\code\Python\LCA\molaqt\doc\General_Specification_v5.html')
        doc_widget = mw.DocWidget(doc_path)
        doc_widget.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(doc_widget, mw.DocWidget)

    # def test_parameters_editor2(self):
    #     spec = ms.ScheduleSpecification()
    #     parameters_editor2 = mw.ParametersEditor2(self.model_config['sets'], self.model_config['parameters'], spec,
    #                                               self.lookup)
    #     parameters_editor2.show()
    #     parameters_editor2.resize(800, 600)
    #
    #     if 'IGNORE_EXEC' not in os.environ:
    #         app.exec()
    #     self.assertIsInstance(parameters_editor2, mw.ParametersEditor2)

    def test_configuration_widget(self):
        spec = ms.ScheduleSpecification()
        config_widget = mw.ConfigurationWidget(spec)
        config_widget.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(config_widget, mw.ConfigurationWidget)

    def test_about_widget(self):
        about_widget = mw.AboutWidget(self.system_setting)
        about_widget.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(about_widget, mw.AboutWidget)


class TestProcessFlow(TestCase):
    # get lookups from db
    conn = di.get_sqlite_connection()
    lookup = dv.LookupTables(conn)

    setting = mqu.system_settings(testing=True)
    config_path = setting['config_path'].joinpath('test_custom_controller.json')

    # load test configuration file
    with open(str(config_path)) as jf:
        model_config = json.load(jf)

    spec = ms.SelectionSpecification()

    def test_init(self):
        process_flow = mw.ProcessFlow(self.model_config['sets'], self.model_config['parameters'],
                                      self.spec, self.lookup, self.conn)
        process_flow.show()
        process_flow.resize(1200, 600)

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        pass
