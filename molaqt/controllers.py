from pathlib import Path
from PyQt5.QtWidgets import QTextEdit, QTabWidget, QWidget, QHBoxLayout

import mola.dataimport as di
import mola.dataview as dv
import mola.utils as mu
import molaqt.build as mb
import molaqt.run as mr
import molaqt.widgets as mw


class Controller(QWidget):
    """
    A Controller is a collection of widgets with which to construct an optimisation problem from a specification.
    Concrete implementations are derived from this class.
    """

    def __init__(self, user_config):
        super().__init__()
        self.saved = False
        self.user_config = user_config
        self.spec = mu.create_specification(user_config['specification'], user_config['settings'])
        print("*** Specification settings:", user_config['settings'])

    def get_config(self):
        """
        Create dict for model configuration file representing current model state
        :return: dict
        """
        config = {
            'settings': self.spec.settings,
            'doc_path': self.user_config['doc_path'],
            'specification': str(self.spec.__class__),
            'controller': 'StandardController',
            'db_file': self.db_file,
            'sets': self.sets_editor.sets,
            'parameters': self.parameters_editor.get_parameters(),
        }

        return config


class CustomController(Controller):

    def __init__(self, user_config):

        super().__init__(user_config)

        # instantiate db connection from config
        self.db_file = user_config['db_file']
        self.conn = di.get_sqlite_connection(self.db_file)

        # get lookups from db
        self.lookup = dv.LookupTables(self.conn)

        # add widgets for sets, parameters, build, run
        self.sets_editor = mw.SetsEditor(user_config['sets'], self.spec, self.lookup)
        self.parameters_editor = mw.ParametersEditor(self.sets_editor.sets, user_config['parameters'],
                                                     self.spec, self.lookup)
        self.model_run = mr.ModelRun(self.lookup, self.spec)
        self.model_build = mb.ModelBuild(self)

        # initialize tab screen
        self.tabs = QTabWidget()

        # documentation tab for specification
        self.documentation = None
        if 'doc_path' in user_config and user_config['doc_path'] != '':
            doc_path = Path(user_config['doc_path'])
            if doc_path.exists():
                self.documentation = mw.DocWidget(doc_path)

        # processes and flows
        self.process_flow = mw.ProcessFlow(user_config['sets'], user_config['parameters'],
                                           self.spec, self.lookup, self.conn)

        # Add tabs
        # self.tabs.addTab(self.sets_editor, "Sets")
        self.tabs.addTab(self.documentation, "Documentation")
        self.tabs.addTab(self.process_flow, "Processes and Flows")
        self.tabs.addTab(self.parameters_editor, "Parameters")
        self.tabs.addTab(self.model_build, "Build")
        self.tabs.addTab(self.model_run, "Run")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)
        self.setLayout(layout)


class StandardController(Controller):

    def __init__(self, user_config):

        super().__init__(user_config)

        # instantiate db connection from config
        self.db_file = user_config['db_file']
        self.conn = di.get_sqlite_connection(self.db_file)

        # get lookups from db
        self.lookup = dv.LookupTables(self.conn)

        # add widgets for sets, parameters, build, run
        self.sets_editor = mw.SetsEditor(user_config['sets'], self.spec, self.lookup)
        self.parameters_editor = mw.ParametersEditor(self.sets_editor.sets, user_config['parameters'],
                                                  self.spec, self.lookup)
        self.model_run = mr.ModelRun(self.lookup, self.spec)
        self.model_build = mb.ModelBuild(self)

        # initialize tab screen
        self.tabs = QTabWidget()

        # documentation tab for specification
        self.documentation = None
        if 'doc_path' in user_config and user_config['doc_path'] != '':
            doc_path = Path(user_config['doc_path'])
            if doc_path.exists():
                self.documentation = mw.DocWidget(doc_path)

        # high-level configuration
        self.configure = mw.ConfigurationWidget(self.spec)

        # Add tabs
        self.tabs.addTab(self.documentation, "Documentation")
        self.tabs.addTab(self.configure, "Configure")
        self.tabs.addTab(self.sets_editor, "Sets")
        self.tabs.addTab(self.parameters_editor, "Parameters")
        self.tabs.addTab(self.model_build, "Build")
        self.tabs.addTab(self.model_run, "Run")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)
        self.setLayout(layout)




