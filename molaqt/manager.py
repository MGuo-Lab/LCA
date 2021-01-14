import sys
import os
import json
from PyQt5.QtWidgets import QWidget, QTreeWidget, QLabel, QTreeWidgetItem, QAction, \
    QMessageBox, QSplitter, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
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
        db_name = 'ecoinvent_36_apos_lci_20200206'
        self.db_tree = QTreeWidget()
        self.db_tree.setHeaderLabels(['Database'])
        self.db_tree.setMinimumWidth(250)
        self.db_item = QTreeWidgetItem(self.db_tree, [db_name])
        self.db_item.setExpanded(True)
        config_item = []
        for cf in os.listdir(system['config_path']):
            config_item.append(QTreeWidgetItem(self.db_item, [cf]))
        self.db_tree.itemDoubleClicked.connect(self.item_double_clicked)

        # context menu for db tree
        self.db_tree.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.delete_model_action = QAction("Delete model")
        self.delete_model_action.triggered.connect(self.delete_model)
        self.db_tree.addAction(self.delete_model_action)
        self.rename_model_action = QAction("Rename model")
        self.rename_model_action.triggered.connect(self.rename_model)
        self.db_tree.addAction(self.rename_model_action)

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
            self.set_controller(config_file)

    def new_model(self, config_file, specification_class, controller_class, database):
        self.controller_config_file = config_file

        # get a new config dict
        new_config = mqu.get_new_config(specification_class, database)

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
                'Delete model ' + model_name,
                'Confirm delete model ' + model_name + ' from ' + db_index.text(0) + '?',
                QMessageBox.Yes | QMessageBox.No
            )
            if choice == QMessageBox.Yes:
                db_index.removeChild(index)
                self.replace_controller(QLabel())
                os.remove(self.system['config_path'].joinpath(model_name))
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
                old_config_file = self.system['config_path'].joinpath(model_name)
                new_model_name = dialog.new_model_name.text()
                new_config_file = self.system['config_path'].joinpath(new_model_name)
                if new_config_file.exists():
                    QMessageBox.about(self, "Error", "Configuration file " + str(new_config_file.absolute()) +
                                      " already exists")
                elif self.controller is not None and not self.controller.saved:
                    QMessageBox.about(self, "Error", "Model not saved")
                else:
                    db_index.removeChild(index)
                    if self.controller is not None:
                        self.replace_controller(QLabel())
                    os.rename(old_config_file, new_config_file)
                    qtw = QTreeWidgetItem(self.db_item, [new_model_name])
                    db_index.addChild(qtw)
                    self.db_tree.clearSelection()
                    qtw.setSelected(True)
                    print("Renamed", model_name, 'to', dialog.new_model_name)

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
            class_ = getattr(mc, user_config['controller'])
            new_controller = class_(user_config)
        else:
            new_controller = mc.StandardController(user_config)

        self.replace_controller(new_controller)

    def replace_controller(self, new_controller):
        self.splitter.replaceWidget(1, new_controller)
        self.splitter.update()
        self.splitter.setStretchFactor(1, 2)
        self.controller = new_controller

    def add_database(self, db_file):
        db_name = os.path.splitext(os.path.basename(db_file))[0]
        self.db_item = QTreeWidgetItem(self.db_tree, [db_name])
        self.db_item.setSelected(True)
