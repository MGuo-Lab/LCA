import sys
import json
import os
import webbrowser
from zipfile import ZipFile
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel
from PyQt5.QtWidgets import QMessageBox, QAction, QTreeWidgetItem
from PyQt5.QtGui import QIcon
import molaqt.dbview as dbv
import molaqt.manager as mt
import molaqt.dialogs as md
import molaqt.widgets as mw
import molaqt.utils as mu
import molaqt.controllers as mc


class MolaMainWindow(QMainWindow):
    """
    Main window for the mola qt application. It defines the menus, toolbars and main widget.
    """

    def __init__(self):
        super(MolaMainWindow, self).__init__()

        # general configuration
        self.development = False
        self.system = mu.system_settings(development=True)

        self.setGeometry(50, 50, 800, 600)
        self.setWindowTitle(self.system['app_name'])
        self.setWindowIcon(QIcon('images/python-logo.png'))
        # self.statusBar()

        # model configuration
        new_model_action = QAction("&New ...", self)
        new_model_action.triggered.connect(self.new_model)
        save_model_action = QAction("&Save", self)
        save_model_action.triggered.connect(self.save_model)
        close_model_action = QAction("&Close", self)
        close_model_action.triggered.connect(self.close_model)
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Alt+E")
        exit_action.setStatusTip('Exit mola')
        exit_action.triggered.connect(self.close_application)

        # database
        import_sqlite_db_action = QAction("&Import sqlite ...", self)
        import_sqlite_db_action.setStatusTip('Import sqlite database')
        import_sqlite_db_action.triggered.connect(self.import_sqlite_database)
        open_db_action = QAction("&Open ...", self)
        open_db_action.setStatusTip('Open database')
        open_db_action.triggered.connect(self.open_database)

        # help
        general_specification_v5_action = QAction("&General Specification v5", self)
        general_specification_v5_action.triggered.connect(self.general_specification_v5)
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.about)

        # menus
        main_menu = self.menuBar()
        model_menu = main_menu.addMenu('&Model')
        model_menu.addAction(new_model_action)
        model_menu.addAction(save_model_action)
        model_menu.addAction(close_model_action)
        model_menu.addAction(exit_action)

        db_menu = main_menu.addMenu('&Database')
        db_menu.addAction(import_sqlite_db_action)
        db_menu.addAction(open_db_action)

        help_menu = main_menu.addMenu('&Help')
        help_menu.addAction(general_specification_v5_action)
        help_menu.addAction(about_action)

        self.manager = mt.ModelManager(self.system)
        self.db_view = []
        self.setCentralWidget(self.manager)
        self.show()

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    def general_specification_v5(self):
        url = self.system['doc_path'].joinpath('General_Specification_v5.html').resolve().as_uri()
        new = 2  # new tab
        webbrowser.open(url, new=new)

    def about(self):
        self.about_widget = mw.AboutWidget(self.system)

    def close_application(self):
        choice = QMessageBox.question(self, 'Exit ' + self.system['app_name'], "Confirm exit?",
                                      QMessageBox.Yes | QMessageBox.No)
        if choice == QMessageBox.Yes:
            print("Exit", self.app_name)
            sys.exit()
        else:
            pass

    def import_sqlite_database(self):
        zip_filter = 'zip files (*.zip)'
        # zip_name = QFileDialog.getOpenFileName(self, 'Import sqlite database', str(Path.home()), zip_filter)
        zip_name = QFileDialog.getOpenFileName(self, 'Import sqlite database', 'Z:\data\openlca\sqlite\system', zip_filter)

        try:
            print('Uncompressing', zip_name[0], 'to', self.system['data_path'])
            with ZipFile(zip_name[0], 'r') as zr:
                zr.extractall(self.system['data_path'])
            db_path = os.path.splitext(self.system['data_path'].joinpath(zip_name[0]))[0]
            self.manager.add_database(db_path)
        except:
            QMessageBox.critical(self, 'Error', 'Cannot uncompress ' + zip_name[0],
                                 QMessageBox.Ok)

    def open_database(self):
        sqlite_filter = 'sqlite files (*.sqlite)'
        db_name = QFileDialog.getOpenFileName(self, 'Open database', str(self.system['data_path']),
                                              sqlite_filter)
        print(db_name)
        if db_name[0] != '':
            db_view = dbv.DbView(db_name[0])
            self.db_view.append(db_view)
            db_view.show()
        else:
            print('Cancelled open database')

    def new_model(self):
        dialog = md.NewModelDialog(parent=self)
        if dialog.exec():
            name, specification_class, controller_class, database = dialog.get_inputs()
            config_file = self.system['config_path'].joinpath(name)
            if config_file.exists():
                QMessageBox.about(self, "Error", "Configuration file " + str(config_file.absolute()) +
                                  " already exists")
            else:
                item = QTreeWidgetItem(self.manager.db_item, [name])
                self.manager.db_tree.clearSelection()
                item.setSelected(True)
                self.manager.new_model(config_file, specification_class, controller_class, database)
                self.save_model()

    def save_model(self):
        try:
            if isinstance(self.manager.controller, mc.Controller):
                # TODO this should go into the Controller class
                config = self.manager.controller.get_config()
                with open(str(self.manager.controller_config_file), 'w') as fp:
                    json.dump(config, fp, indent=4)
                self.manager.controller.saved = True
                self.setWindowTitle(str(self.manager.controller_config_file) + ' - molaqt')
                print('Saved model configuration to ', str(self.manager.controller_config_file))
            else:
                print("Nothing to save")

        except Exception as e:
            self.dialog_critical(str(e))

    def close_model(self):
        if self.manager.controller_config_file is not None:
            choice = None
            if not self.manager.controller.saved:
                choice = QMessageBox.question(self, 'Model not saved', "Confirm close?",
                                              QMessageBox.Yes | QMessageBox.No)

            if choice == QMessageBox.Yes or self.manager.controller.saved:
                self.manager.replace_controller(QLabel())
                self.setWindowTitle(self.system['app_name'])
                print('Closed model', self.manager.controller_config_file)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = MolaMainWindow()
    sys.exit(app.exec_())
