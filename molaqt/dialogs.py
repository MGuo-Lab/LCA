from PyQt5.QtWidgets import QDialog, QLineEdit, QDialogButtonBox, QFormLayout, QApplication
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget, QApplication, QDesktopWidget
from PyQt5.QtGui import QPixmap, QPainter, QFont
from PyQt5.Qt import QPoint
from PyQt5.QtCore import Qt
import mola.specification5 as ms
import molaqt.controllers as mqc


class NewModelDialog(QDialog):
    def __init__(self, parent=None, db_files=None):
        super().__init__(parent)
        self.setWindowTitle("New Model")

        self.name = QLineEdit(self)
        self.name.setText('test_model')
        self.specification = QComboBox(self)

        # builder combobox
        self.builder = QComboBox(self)
        self.builders = None
        self.builder_class = {
            "StandardController": mqc.StandardController,
            "CustomController": mqc.CustomController}

        # specification combobox
        self.specification.currentIndexChanged.connect(self.specification_changed)
        self.specifications = {"General Specification": ms.ScheduleSpecification,
                               "Selection Specification": ms.SelectionSpecification}
        for spec in self.specifications:
            self.specification.addItem(spec)

        self.database = QComboBox(self)
        # FIXME turn into hash
        self.db_files = {f.stem: f for f in db_files}
        # self.database.addItem("C:/data/openlca/sqlite/system/CSV_juice_ecoinvent_36_apos_lci_20200206_20201029-102818.sqlite")
        self.database.addItems(self.db_files.keys())
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)

        layout = QFormLayout(self)
        layout.addRow("Name", self.name)
        layout.addRow("Specification", self.specification)
        layout.addRow("Builder", self.builder)
        layout.addRow("Database", self.database)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def specification_changed(self, index):
        spec_name = list(self.specifications.keys())
        spec_class = list(self.specifications.values())
        print("Specification changed to", spec_name[index])
        self.builder.clear()
        self.builders = spec_class[index].controllers
        for builder in self.builders:
            self.builder.addItem(builder)

    def get_inputs(self):
        spec_class = list(self.specifications.values())
        builder_text = list(self.builders.values())
        current_spec_class = spec_class[self.specification.currentIndex()]
        current_builder_class = self.builder_class[builder_text[self.builder.currentIndex()]]
        return self.name.text(), current_spec_class, \
               current_builder_class, self.db_files[self.database.currentText()]


class RenameModelDialog(QDialog):

    def __init__(self, current_model_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename Model " + current_model_name)

        self.new_model_name = QLineEdit(self)
        self.new_model_name.setText(current_model_name)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)

        layout = QFormLayout(self)
        layout.addRow("New model name", self.new_model_name)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)


if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)
    dialog = NewModelDialog()
    if dialog.exec():
        print(dialog.get_inputs())
    exit(0)
