from pathlib import Path
from PyQt5.QtWidgets import QTabWidget, QWidget, QHBoxLayout

import mola.dataimport as di
import mola.dataview as dv
import mola.build as mb
import molaqt.build as mqb
import molaqt.run as mr
import molaqt.widgets as mw


class Controller(QWidget):
    """
    A Controller is a collection of widgets with which to construct an optimisation problem from a specification.
    Implementations are derived from this class.
    """

    def __init__(self, user_config):
        super().__init__()
        self.saved = False
        self.user_config = user_config
        self.spec = mb.create_specification(user_config['specification'], user_config['settings'])

        # merge user sets and parameters into spec defaults
        self.sets = self.spec.get_default_sets()
        self.sets.update(user_config['sets'])
        self.parameters = self.spec.get_default_parameters(self.sets)
        self.parameters.update(user_config['parameters'])

    def get_config(self):
        """
        Create dict for model configuration file representing current model state
        :return: dict
        """
        config = {
            'settings': self.spec.settings,
            'doc_path': self.user_config['doc_path'],
            'specification': str(self.spec.__class__),
            'controller': self.user_config['controller'],
            'db_file': self.db_file,
            'sets': self.sets,
            'parameters': self.get_parameters(),
        }

        return config

    def get_parameters(self):
        return super.get_parameters()


class CustomController(Controller):

    def __init__(self, user_config):

        super().__init__(user_config)

        # instantiate db connection from config
        self.db_file = user_config['db_file']
        self.conn = di.get_sqlite_connection(self.db_file)

        # get lookups from db
        self.lookup = dv.LookupTables(self.conn)

        # add widgets for objective, network, build, run
        self.obj = mw.ObjectiveWidget(self.lookup, self.sets['KPI'])
        self.process_flow = mw.ProcessFlow(self.sets, self.parameters,
                                           self.spec, self.lookup, self.conn)
        p = {k: v for k, v in self.parameters.items() if k != 'J'}
        self.parameters_editor = mw.ParametersEditor(self.sets, p, self.spec, self.lookup)
        self.model_run = mr.ModelRun(self.lookup)
        self.model_build = mqb.ModelBuild(self)

        # initialize tab screen
        self.tabs = QTabWidget()

        # documentation tab for specification
        self.documentation = None
        if 'doc_path' in user_config and user_config['doc_path'] != '':
            doc_path = Path(user_config['doc_path'])
            if doc_path.exists():
                self.documentation = mw.DocWidget(doc_path)

        # Add tabs
        self.tabs.addTab(self.documentation, "Documentation")
        self.tabs.addTab(self.obj, "Objective")
        self.tabs.addTab(self.process_flow, "Processes and Flows")
        self.tabs.addTab(self.parameters_editor, "Parameters")
        self.tabs.addTab(self.model_build, "Build")
        self.tabs.addTab(self.model_run, "Run")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def get_parameters(self):
        self.parameters = self.parameters_editor.get_parameters()
        # TODO: only allow process_flow to alter J
        p = self.process_flow.get_parameters()
        self.parameters.update({'J': p['J']})
        return self.parameters


class StandardController(Controller):

    def __init__(self, user_config):

        super().__init__(user_config)

        # instantiate db connection from config
        self.db_file = user_config['db_file']
        self.conn = di.get_sqlite_connection(self.db_file)

        # get lookups from db
        self.lookup = dv.LookupTables(self.conn)

        # add widgets for sets, parameters, build, run
        self.sets_editor = mw.SetsEditor(self.sets, self.spec, self.lookup)
        self.parameters_editor = mw.ParametersEditor(self.sets, self.parameters,
                                                     self.spec, self.lookup)
        self.model_run = mr.ModelRun(self.lookup)
        self.model_build = mqb.ModelBuild(self)

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

    def get_parameters(self):
        self.parameters = self.parameters_editor.get_parameters()
        return self.parameters

