import io
from PyQt5.QtWidgets import QWidget, QPushButton, QTreeWidget, QTableView, QGridLayout, QTextEdit, \
    QTreeWidgetItem, QLabel, QHeaderView, QCheckBox, QComboBox
import pyomo.environ as pe
import pandas as pd

import mola.output as mo
import molaqt.datamodel as md


class ModelRun(QWidget):

    def __init__(self, lookup):

        super().__init__()
        self._concrete_model = None
        self.results = None
        self.lookup = lookup

        # button
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_button_clicked)

        # checkboxes
        self.nonzero_checkbox = QCheckBox('Non-zero flows')
        self.nonzero_checkbox.toggle()
        self.nonzero_checkbox.clicked.connect(self.checkbox_clicked)
        self.distinct_levels_checkbox = QCheckBox('Distinct levels')
        self.distinct_levels_checkbox.toggle()
        self.distinct_levels_checkbox.clicked.connect(self.checkbox_clicked)

        # objectives
        self.objective_combobox = QComboBox()
        self.objective_combobox.currentIndexChanged.connect(self.objective_changed)

        # add list widget for output
        self.run_tree = QTreeWidget()
        self.run_tree.setHeaderLabels(['Component'])
        self.run_tree.itemClicked.connect(self.run_item_clicked)

        # add table for run content
        self.run_table = QTableView()
        self.run_table.setSelectionBehavior(QTableView.SelectRows)

        # component documentation
        self.cpt_doc = QLabel()

        # arrange widgets in grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.objective_combobox, 0, 0)
        grid_layout.addWidget(self.run_button, 1, 0)
        grid_layout.addWidget(self.run_tree, 2, 0)
        grid_layout.addWidget(self.cpt_doc, 0, 1)
        grid_layout.addWidget(self.distinct_levels_checkbox, 0, 2)
        grid_layout.addWidget(self.nonzero_checkbox, 0, 3)
        grid_layout.addWidget(self.run_table, 1, 1, 2, 3)
        grid_layout.setColumnStretch(1, 2)
        self.setLayout(grid_layout)

    @property
    def concrete_model(self):
        return self._concrete_model

    @concrete_model.setter
    def concrete_model(self, model):
        print('Concrete model changed in ModelRun')
        self._concrete_model = model
        self.objectives = {}
        for i, obj in enumerate(model.component_objects(pe.Objective)):
            self.objective_combobox.addItem(obj.name)
            # activate first objective
            if i == 0:
                obj.activate()
            else:
                obj.deactivate()

    def objective_changed(self):
        for i, obj in enumerate(self._concrete_model.component_objects(pe.Objective)):
            if i == self.objective_combobox.currentIndex():
                obj.activate()
            else:
                obj.deactivate()

    def checkbox_clicked(self):
        if self.run_tree:
            item = self.run_tree.selectedItems()
            self.run_item_clicked(item[0])

    def run_button_clicked(self):
        print('Run button clicked')
        if self._concrete_model is not None:
            opt = pe.SolverFactory("glpk")
            self.results = opt.solve(self.concrete_model)

            self.run_tree.clear()
            var_item = QTreeWidgetItem(self.run_tree, ['Variables'])
            for var in self._concrete_model.component_objects(pe.Var, active=True):
                QTreeWidgetItem(var_item, [var.name])

            objective_item = QTreeWidgetItem(self.run_tree, ['Objective'])
            for obj in self._concrete_model.component_objects(pe.Objective):
                if obj.active:
                    QTreeWidgetItem(objective_item, [obj.name])

            log_item = QTreeWidgetItem(self.run_tree, ['Log'])
        else:
            print("No successful build")

    def run_item_clicked(self, item):
        print('Run item', item.text(0), 'clicked')
        output = io.StringIO()
        if item.parent() is not None:
            if item.parent().text(0) == 'Variables':
                cpt = self._concrete_model.find_component(item.text(0))
                self.cpt_doc.setText(item.text(0) + ': ' + cpt.doc)
                df = mo.get_entity(cpt, self.lookup, units=True,
                                   non_zero=self.nonzero_checkbox.isChecked(),
                                   distinct_levels=self.distinct_levels_checkbox.isChecked()
                                   )
                run_model = md.PandasModel(df)
                self.run_table.setModel(run_model)
                self.run_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.run_table.resizeRowsToContents()
            elif item.parent().text(0) == 'Objective':
                cpt = self._concrete_model.find_component(item.text(0))
                self.cpt_doc.setText(cpt.doc)
                df = mo.get_entity(cpt, self.lookup, units=True)
                run_model = md.PandasModel(df)
                self.run_table.setModel(run_model)

        if item.text(0) == 'Log':
            self.results.write(ostream=output)
            self.log = QTextEdit()
            self.log.setWindowTitle("Log file")
            self.log.resize(800, 600)
            self.log.setText(output.getvalue())
            self.log.show()
        output.close()

