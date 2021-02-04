import io
from PyQt5.QtWidgets import QWidget, QPushButton, QTreeWidget, QTableView, QGridLayout, QTextEdit, \
    QTreeWidgetItem, QLabel, QHeaderView, QCheckBox
import pyomo.environ as pe
import mola.output as mo
import molaqt.datamodel as md


class ModelRun(QWidget):

    def __init__(self, lookup):

        super().__init__()
        self.concrete_model = None
        self.results = None
        self.lookup = lookup

        # button
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_button_clicked)

        # checkbox to show zero values only
        self.nonzero_checkbox = QCheckBox('Non-zero flows')
        self.nonzero_checkbox.toggle()
        self.nonzero_checkbox.clicked.connect(self.nonzero_checkbox_clicked)

        # add list widget for output
        self.run_tree = QTreeWidget()
        self.run_tree.setHeaderLabels(['Component'])
        self.run_tree.itemClicked.connect(self.run_item_clicked)

        # add table for run content
        self.run_table = QTableView()
        self.run_table.setSelectionBehavior(QTableView.SelectRows);

        # component documentation
        self.cpt_doc = QLabel()

        # arrange widgets in grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.run_button, 0, 0)
        grid_layout.addWidget(self.run_tree, 1, 0)
        grid_layout.addWidget(self.cpt_doc, 0, 1)
        grid_layout.addWidget(self.nonzero_checkbox, 0, 2)
        grid_layout.addWidget(self.run_table, 1, 1, 1, 2)
        grid_layout.setColumnStretch(1, 2)
        self.setLayout(grid_layout)

    def nonzero_checkbox_clicked(self):
        if self.run_tree:
            item = self.run_tree.selectedItems()
            self.run_item_clicked(item[0])

    def run_button_clicked(self):
        print('Run button clicked')
        if self.concrete_model is not None:
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
                df = mo.get_entity(cpt, self.lookup, units=True)
                if self.nonzero_checkbox.isChecked():
                    numeric_cols = df.select_dtypes('number').columns
                    df = df[(df[numeric_cols] > 0).any(axis=1)]
                run_model = md.PandasModel(df)
                self.run_table.setModel(run_model)
                self.run_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.run_table.resizeRowsToContents()

        if item.text(0) == 'Log':
            self.results.write(ostream=output)
            self.log = QTextEdit()
            self.log.setWindowTitle("Log file")
            self.log.resize(800, 600)
            self.log.setText(output.getvalue())
            self.log.show()
        output.close()

