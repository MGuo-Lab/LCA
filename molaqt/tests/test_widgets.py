# unit tests of small widgets
import webbrowser
import os
import sys
from unittest import TestCase
from pathlib import Path

import pandas as pd
from PyQt5.QtWidgets import QApplication

import mola.dataimport as di
import mola.dataview as dv
import molaqt.utils as mqu
import mola.build as mb
import molaqt.widgets as mw

app = QApplication(sys.argv)
setting = mqu.system_settings(testing=True)

# get lookups from db - TODO: mock this db
conn = di.get_sqlite_connection()
lookup = dv.LookupTables(conn)


class Widgets(TestCase):
    model_config = mb.get_config(setting['config_path'].joinpath('Orange_Toy_Model.json'))
    spec = mb.create_specification(model_config['specification'])

    def test_lookup_widget(self):
        lookup_widget = mw.LookupWidget(lookup, 'P_m')

        if 'IGNORE_EXEC' not in os.environ:
            ok = lookup_widget.exec()
            if ok:
                # FIXME simulate lookup table and selecting lookups
                print(lookup_widget.get_elements())
        self.assertIsInstance(lookup_widget, mw.LookupWidget)

    def test_sets_editor(self):
        sets_editor = mw.SetsEditor(self.model_config['sets'], self.spec, lookup)
        sets_editor.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(sets_editor, mw.SetsEditor)

    def test_indexed_sets_editor(self):
        setting = mqu.system_settings(testing=True)
        config_path = setting['config_path'].joinpath('Kondili_State_Task_Network.json')
        config = mb.get_config(config_path)
        spec = mb.create_specification(config['specification'])
        indexed_sets_editor = mw.IndexedSetsEditor(config['indexed_sets'], config['sets'], spec, lookup)
        indexed_sets_editor.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(indexed_sets_editor, mw.IndexedSetsEditor)

    def test_parameters_editor(self):
        parameters_editor = mw.ParametersEditor(self.model_config['sets'], self.model_config['parameters'], self.spec,
                                                lookup)
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

    def test_configuration_widget(self):
        config_widget = mw.ConfigurationWidget(self.spec)
        config_widget.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(config_widget, mw.ConfigurationWidget)

    def test_about_widget(self):
        about_widget = mw.AboutWidget(mqu.system_settings(testing=True))
        about_widget.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(about_widget, mw.AboutWidget)


class TestProcessFlow(TestCase):
    model_config = mb.get_config(setting['config_path'].joinpath('test_custom_controller.json'))
    spec = mb.create_specification(model_config['specification'])

    def test_init(self):
        process_flow = mw.ProcessFlow(self.model_config['sets'], self.model_config['parameters'],
                                      self.spec, lookup, conn)
        process_flow.show()
        process_flow.resize(1200, 600)

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        pass


class TestLinkParameterDiagram(TestCase):
    model_config = mb.get_config(setting['config_path'].joinpath('Orange_Toy_Model.json'))
    spec = mb.create_specification(model_config['specification'])

    # rebuild parameters
    pars = mb.build_parameters(model_config['sets'], model_config['parameters'], spec)

    def test_init(self):
        param = 'J'

        # convert parameter json to DataFrame
        df = pd.DataFrame(self.pars[param])
        df['Value'] = 1
        link_diagram = mw.LinkParameterDiagram(df, param, self.spec, lookup)

        html_path = link_diagram.get_html_path()
        url = html_path.resolve().as_uri()
        webbrowser.open(url, new=2)  # new tab

        self.assertIsInstance(html_path, Path)


class TestObjectiveWidget(TestCase):
    model_config = mb.get_config(setting['config_path'].joinpath('test_custom_controller.json'))

    def test_init(self):
        obj_widget = mw.ObjectiveWidget(lookup, self.model_config['sets']['KPI'])
        obj_widget.show()
        obj_widget.resize(640, 480)

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        pass
