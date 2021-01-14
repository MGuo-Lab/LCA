import sys
import json
import re
import importlib
import pandas as pd
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QListWidget, QTableView, QGridLayout, QMessageBox
from PyQt5.QtCore import QAbstractTableModel, Qt
import mola.output as mo
import mola.utils as mu
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

        # arrange widgets in grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.build_button, 0, 0)
        grid_layout.addWidget(self.build_list, 1, 0)
        grid_layout.addWidget(self.build_table, 0, 1, 2, 1)
        grid_layout.setColumnStretch(1, 2)
        self.setLayout(grid_layout)

    def build_button_clicked(self):
        print('Build started')
        try:
            config = self.controller.get_config()
            self.concrete_model = mu.build_instance(config, self.controller.spec.settings)
            if self.controller.model_run is not None:
                self.controller.model_run.concrete_model = self.concrete_model
            self.build_list.clear()
            self.build_list.addItems(self.build_items)
            print('Build completed')
        except Exception as e:
            print(e)
            self.dialog_critical(str(e))

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
            #self.build_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # config_file = Path('Z:/work/code/Python/LCA/config/model_config.json')
    config_file = Path('/config/test_custom_controller.json')
    with open(config_file) as fp:
        config = json.load(fp)
    gui = ModelBuild(config)
    gui.show()
    sys.exit(app.exec_())
