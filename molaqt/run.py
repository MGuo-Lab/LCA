import sys
import io
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QTreeWidget, QTableView, QGridLayout, QTextEdit, \
    QTreeWidgetItem, QLabel, QRadioButton
import pyomo.environ as pe
import mola.output as mo
import mola.dataimport as di
import mola.dataview as dv
import molaqt.datamodel as md


class ModelRun(QWidget):

    def __init__(self, lookup, spec):

        super().__init__()
        self.concrete_model = None
        self.results = None
        self.lookup = lookup
        self.spec = spec

        # button
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_button_clicked)

        # add list widget for output
        self.run_tree = QTreeWidget()
        self.run_tree.setHeaderLabels(['Component'])
        self.run_tree.itemClicked.connect(self.run_item_clicked)

        # add table for run content
        self.run_table = QTableView()

        # component documentation
        self.cpt_doc = QLabel()

        # arrange widgets in grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.run_button, 0, 0)
        grid_layout.addWidget(self.run_tree, 1, 0)
        grid_layout.addWidget(self.cpt_doc, 0, 1)
        grid_layout.addWidget(self.run_table, 1, 1)
        grid_layout.setColumnStretch(1, 2)
        self.setLayout(grid_layout)

    def run_button_clicked(self):
        print('Run button clicked')
        if self.concrete_model is not None:
            self.concrete_model.dd.pprint()
            self.concrete_model.obj1.deactivate()
            self.concrete_model.obj2.deactivate()
            self.concrete_model.obj.activate()
            opt = pe.SolverFactory("glpk")
            self.results = opt.solve(self.concrete_model)

            self.run_tree.clear()
            var_item = QTreeWidgetItem(self.run_tree, ['Variables'])
            for var in self.concrete_model.component_objects(pe.Var, active=True):
                QTreeWidgetItem(var_item, [var.name])

            log_item = QTreeWidgetItem(self.run_tree, ['Log'])
        else:
            print("No successful build")

    def run_item_clicked(self, item):
        print('Run item', item.text(0), 'clicked')
        output = io.StringIO()
        if item.parent() is not None:
            if item.parent().text(0) == 'Variables':
                cpt = self.concrete_model.find_component(item.text(0))
                self.cpt_doc.setText(item.text(0) + ': ' + cpt.doc)
                df = mo.get_entity(cpt, self.lookup).reset_index(drop=True)
                run_model = md.PandasModel(df)
                self.run_table.setModel(run_model)
                # self.run_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
                self.run_table.resizeColumnsToContents()
                # self.run_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        if item.text(0) == 'Log':
            self.results.write(ostream=output)
            self.log = QTextEdit()
            self.log.setWindowTitle("Log file")
            self.log.resize(800, 600)
            self.log.setText(output.getvalue())
            self.log.show()
        output.close()

