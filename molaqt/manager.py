import sys
import re
import json
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QTreeWidget, QLabel, QTreeWidgetItem, QAction, \
    QMessageBox, QSplitter, QHBoxLayout
from PyQt5.QtCore import Qt
import molaqt.controllers as mc
import molaqt.dialogs as md
import molaqt.utils as mqu


class ModelManager(QWidget):
    """
    The main window for MolaQT. It manages optimisation models using an openLCA database.
    """

    def __init__(self, system):
        super().__init__()
        self.system = system

        # model config file
        self.controller_config_file = None

        # workflow for building model
        self.controller = QLabel()

        # db tree
        self.db_tree = QTreeWidget()
        self.db_tree.setHeaderLabels(['Database'])
        self.db_tree.setMinimumWidth(250)
        self.db_tree.itemDoubleClicked.connect(self.item_double_clicked)

        # context menu for db tree
        self.db_tree.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.delete_model_action = QAction("Delete model")
        self.delete_model_action.triggered.connect(self.delete_model)
        self.db_tree.addAction(self.delete_model_action)
        self.rename_model_action = QAction("Rename model")
        self.rename_model_action.triggered.connect(self.rename_model)
        self.db_tree.addAction(self.rename_model_action)

        # find the user sqlite databases and add them to db tree
        self.db_items = {}
        db_files = list(system['data_path'].glob('*.sqlite'))
        for db_file in db_files:
            self.db_items[db_file] = QTreeWidgetItem(self.db_tree, [db_file.stem])
            self.db_items[db_file].setExpanded(True)

        # add each model config to its database item by examining db_file entry
        config_item = []
        for cf in system['config_path'].glob('*.json'):
            with open(str(cf)) as fp:
                config_json = json.load(fp)
            if 'db_file' in config_json:
                config_db = Path(config_json['db_file'])
                if config_db.exists():
                    config_item.append(QTreeWidgetItem(self.db_items[config_db], [cf.stem]))

        # arrange widgets in splitter
        box = QHBoxLayout()
        self.splitter = QSplitter()
        self.splitter.addWidget(self.db_tree)
        self.splitter.addWidget(self.controller)
        self.splitter.setStretchFactor(1, 2)
        box.addWidget(self.splitter)

        self.setLayout(box)

    def item_double_clicked(self, item, col):
        if self.db_tree.indexOfTopLevelItem(item) == -1:
            config_file = self.system['config_path'].joinpath(item.text(0))
            print('Loading model', config_file)
            self.set_controller(config_file.with_suffix('.json'))

    def new_model(self, config_file, specification_class, controller_class, database, doc_file):
        self.controller_config_file = config_file

        # get a new config dict
        new_config = mqu.get_new_config(specification_class, database, doc_file, controller_class)

        # instantiate controller using config
        new_controller = controller_class(new_config)

        # open new controller widget
        self.replace_controller(new_controller)

    def delete_model(self):
        index = self.db_tree.selectedItems()[0]
        if index.parent() is not None:
            db_index = index.parent()
            model_name = index.text(0)
            choice = QMessageBox.question(
                self,
                'Delete model',
                'Confirm delete ' + model_name + ' from ' + db_index.text(0) + '?',
                QMessageBox.Yes | QMessageBox.No
            )
            if choice == QMessageBox.Yes:
                db_index.removeChild(index)
                self.replace_controller(QLabel())
                self.system['config_path'].joinpath(model_name).with_suffix('.json').unlink()
                print("Deleted", model_name)
            else:
                pass

    def rename_model(self):
        index = self.db_tree.selectedItems()[0]
        if index.parent() is not None:
            db_index = index.parent()
            model_name = index.text(0)
            dialog = md.RenameModelDialog(current_model_name=model_name, parent=self)
            if dialog.exec():
                old_config_path = self.system['config_path'].joinpath(model_name).with_suffix('.json')
                new_model_name = dialog.new_model_name.text()
                new_config_path = self.system['config_path'].joinpath(new_model_name).with_suffix('.json')
                if new_config_path.exists():
                    QMessageBox.about(self, "Error", "Configuration file " + str(new_config_path.absolute()) +
                                      " already exists")
                elif not isinstance(self.controller, QLabel) and not self.controller.saved:
                    QMessageBox.about(self, "Error", "Model not saved")
                else:
                    db_index.removeChild(index)
                    if self.controller is not None:
                        self.replace_controller(QLabel())
                    old_config_path.rename(new_config_path)
                    qtw = QTreeWidgetItem(db_index, [new_model_name])
                    db_index.addChild(qtw)
                    self.db_tree.clearSelection()
                    qtw.setSelected(True)
                    print("Renamed", model_name, 'to', dialog.new_model_name.text())

    def set_controller(self, config_file):
        self.controller_config_file = config_file
        if self.parent() is not None:
            self.parent().setWindowTitle(str(config_file) + ' - molaqt')

        # get configuration
        if config_file.exists():
            with open(config_file) as fp:
                user_config = json.load(fp)
        else:
            sys.exit("Cannot find configuration file")

        # instantiate controller using config if available otherwise default to StandardController
        if 'controller' in user_config:
            search = re.search("<class '(.*?)\.(.*?)\.(.*?)'>", user_config['controller'])
            class_name = search.group(3)
            class_ = getattr(mc, class_name)
            new_controller = class_(user_config)
        else:
            new_controller = mc.StandardController(user_config)

        self.replace_controller(new_controller)

    def replace_controller(self, new_controller):
        # TODO: remove doc
        self.splitter.replaceWidget(1, new_controller)
        self.splitter.update()
        self.splitter.setStretchFactor(1, 2)
        self.controller = new_controller

    def add_database(self, db_path):
        db_item = QTreeWidgetItem(self.db_tree, [db_path.stem])
        self.db_items[db_path] = db_item
        db_item.setSelected(True)
