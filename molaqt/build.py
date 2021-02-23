import traceback
import io
from contextlib import redirect_stdout

import pandas as pd
from PyQt5.QtWidgets import QWidget, QPushButton, QListWidget, QTableView, QGridLayout, QMessageBox,\
    QHeaderView, QTextEdit

from pyomo.core.base.units_container import UnitsError

import mola.output as mo
import mola.build as mb
import molaqt.datamodel as dm


class ModelBuild(QWidget):

    def __init__(self, controller):

        super().__init__()
        self.concrete_model = None
        self.controller = controller

        # button
        self.build_button = QPushButton("Build")
        self.build_button.clicked.connect(self.build_button_clicked)

        # add list widget for user-defined sets
        self.build_list = QListWidget()
        self.build_items = ['Sets', 'Parameters', 'Constraints', 'Objectives']
        self.build_list.itemClicked.connect(self.build_item_clicked)

        # add table for build content
        self.build_table = QTableView()
        self.build_table.setModel(dm.PandasModel(pd.DataFrame()))
        self.build_table.setSelectionBehavior(QTableView.SelectRows)
        self.build_table.setSelectionMode(QTableView.SingleSelection)
        self.build_table.doubleClicked.connect(self.build_table_row_clicked)

        # arrange widgets in grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.build_button, 0, 0)
        grid_layout.addWidget(self.build_list, 1, 0)
        grid_layout.addWidget(self.build_table, 0, 1, 2, 1)
        grid_layout.setColumnStretch(1, 2)
        self.setLayout(grid_layout)

    def build_table_row_clicked(self):
        model = self.build_table.model()
        cpt_idx = self.build_table.selectedIndexes()
        cpt_name = model.data(cpt_idx[0])
        print('Build table clicked for cpt', cpt_name)

        with io.StringIO() as buf, redirect_stdout(buf):
            self.concrete_model.component(cpt_name).pprint()
            output = buf.getvalue()

        self.cpt_widget = QTextEdit()
        self.cpt_widget.setFontFamily('Courier New')
        self.cpt_widget.setWindowTitle("Model component")
        self.cpt_widget.resize(800, 600)
        self.cpt_widget.setText(output)
        self.cpt_widget.show()

    def build_button_clicked(self):
        print('Build started')
        try:
            config = self.controller.get_config()
            self.concrete_model = mb.build_instance(config, self.controller.spec.settings)
            if self.controller.model_run is not None:
                self.controller.model_run.concrete_model = self.concrete_model
            self.build_list.clear()
            self.build_list.addItems(self.build_items)
            print('Build completed')
        except ValueError as e:
            self.dialog_critical("Unable to find data in database", str(e), traceback.format_exc())
        except UnitsError as e:
            self.dialog_critical("Unit conversion error", str(e), traceback.format_exc())
        except Exception as e:
            self.dialog_critical("Uncaught exception for model build", str(e), traceback.format_exc())

    def build_item_clicked(self, item):
        print('Build item', item.text(), 'clicked')
        if self.concrete_model is not None:
            if item.text() == 'Sets':
                df = mo.get_sets_frame(self.concrete_model)
            elif item.text() == 'Parameters':
                df = mo.get_parameters_frame(self.concrete_model)
            elif item.text() == 'Constraints':
                df = mo.get_constraints_frame(self.concrete_model)
            elif item.text() == 'Objectives':
                df = mo.get_objectives_frame(self.concrete_model)
            else:
                df = pd.DataFrame({'a': [1]})
            self.build_table.setModel(dm.PandasModel(df))
            self.build_table.resizeColumnsToContents()
            # self.build_table.resizeRowsToContents()
            self.build_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def dialog_critical(self, title, text, detailed_text=None):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(title)
        dlg.setText(text)
        dlg.setDetailedText(detailed_text)
        details_box = dlg.findChild(QTextEdit)
        details_box.setFixedSize(600, 400)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()


