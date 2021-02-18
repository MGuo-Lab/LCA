from pathlib import Path
from PyQt5.QtWidgets import QDialog, QLineEdit, QDialogButtonBox, QFormLayout, QFileDialog
from PyQt5.QtWidgets import QComboBox, QApplication, QPushButton, QHBoxLayout, QWidget
import mola.specification5 as ms
import molaqt.controllers as mqc


class NewModelDialog(QDialog):
    def __init__(self, parent=None, db_files=None):
        super().__init__(parent)
        self.setWindowTitle("New Model")

        self.name = QLineEdit(self)
        self.name.setText('test_model')

        # builder combobox
        self.builder = QComboBox(self)
        self.builders = None
        self.builder_class = {
            "StandardController": mqc.StandardController,
            "CustomController": mqc.CustomController}

        # specification combobox
        self.specification = QComboBox(self)
        self.specification.currentIndexChanged.connect(self.specification_changed)
        self.specifications = {cls.name: cls for cls in ms.Specification.__subclasses__()}
        for spec in self.specifications:
            self.specification.addItem(spec)

        # add databases to combobox
        self.database = QComboBox(self)
        self.db_files = {f.stem: f for f in db_files if f != 'None'}
        self.database.addItems(self.db_files.keys())
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)

        # documentation
        self.doc_widget = DocWidget()

        layout = QFormLayout(self)
        layout.addRow("Name", self.name)
        layout.addRow("Specification", self.specification)
        layout.addRow("Controller", self.builder)
        layout.addRow("Database", self.database)
        layout.addRow("Documentation", self.doc_widget)
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
        return (
            self.name.text(),
            current_spec_class,
            current_builder_class,
            self.db_files[self.database.currentText()],
            self.doc_widget.path.text()
        )


class DocWidget(QWidget):

    def __init__(self):
        super().__init__()

        # widgets
        self.path = QLineEdit()
        button = QPushButton('...')
        button.clicked.connect(self.find_file)

        # layout
        layout = QHBoxLayout(self)
        layout.addWidget(self.path)
        layout.addWidget(button)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def find_file(self):
        doc_file = QFileDialog.getOpenFileName(self, 'Open file', str(Path.home()),
                                               "HTML files (*.html)")
        if doc_file[0] != '':
            self.path.setText(doc_file[0])


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


