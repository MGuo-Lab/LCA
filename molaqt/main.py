import sys
import json
import webbrowser
from zipfile import ZipFile

from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel
from PyQt5.QtWidgets import QMessageBox, QAction, QTreeWidgetItem
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

import qrc_resources
import molaqt.dbview as dbv
import molaqt.manager as mt
import molaqt.dialogs as md
import molaqt.widgets as mw
import molaqt.utils as mu
import molaqt.controllers as mc
from molaqt.console import QtConsoleWindow


class MolaMainWindow(QMainWindow):
    """
    Main window for the mola qt application. It defines the menus, toolbars and main widget.
    """

    def __init__(self):
        super(MolaMainWindow, self).__init__()

        # general configuration
        self.development = False
        self.system = mu.system_settings(development=True)
        self.qt_console = None

        self.setGeometry(50, 50, 800, 600)
        self.setWindowTitle(self.system['app_name'])
        self.setWindowIcon(QIcon(":python-logo.png"))
        # self.statusBar()

        # model configuration
        self.new_model_action = QAction(QIcon(":New.svg"), "&New ...", self)
        self.new_model_action.setShortcut("Ctrl+N")
        self.new_model_action.triggered.connect(self.new_model)
        self.save_model_action = QAction(QIcon(":Save.svg"), "&Save", self)
        self.save_model_action.setShortcut("Ctrl+S")
        self.save_model_action.triggered.connect(self.save_model)
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
        self.open_db_action = QAction(QIcon(":Library.svg"), "&Open ...", self)
        self.open_db_action.setStatusTip('Open database')
        self.open_db_action.triggered.connect(self.open_database)

        # help
        general_specification_v5_action = QAction("&General Specification v5", self)
        general_specification_v5_action.triggered.connect(
            lambda: self.open_url(doc_file='General_Specification_v5.html'))
        github_home_action = QAction('&Github Home', self)
        github_home_action.triggered.connect(lambda: self.open_url(url='https://github.com/MGuo-Lab/LCA/wiki'))
        console_action = QAction("Qt Console", self)
        console_action.triggered.connect(self.console)
        self.about_action = QAction(QIcon(":Help.svg"), "&About", self)
        self.about_action.triggered.connect(self.about)

        # menus
        main_menu = self.menuBar()
        model_menu = main_menu.addMenu('&Model')
        model_menu.addAction(self.new_model_action)
        model_menu.addAction(self.save_model_action)
        model_menu.addAction(close_model_action)
        model_menu.addAction(exit_action)

        db_menu = main_menu.addMenu('&Database')
        db_menu.addAction(import_sqlite_db_action)
        db_menu.addAction(self.open_db_action)

        help_menu = main_menu.addMenu('&Help')
        help_menu.addAction(general_specification_v5_action)
        help_menu.addAction(github_home_action)
        help_menu.addAction(console_action)
        help_menu.addAction(self.about_action)

        self._create_toolbars()

        self.manager = mt.ModelManager(self.system)
        self.db_view = []
        self.setCentralWidget(self.manager)
        self.show()

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    def open_url(self, doc_file=None, url=None):
        if doc_file:
            url = self.system['doc_path'].joinpath(doc_file).resolve().as_uri()
        webbrowser.open(url, new=2)  # new tab

    def about(self):
        self.about_widget = mw.AboutWidget(self.system)

    def console(self):
        self.qt_console = QtConsoleWindow(self.manager)
        self.qt_console.show()

    def shutdown_kernel(self):
        if self.qt_console is not None:
            self.qt_console.shutdown_kernel()

    def close_application(self):
        choice = QMessageBox.question(self, 'Exit ' + self.system['app_name'], "Confirm exit?",
                                      QMessageBox.Yes | QMessageBox.No)
        if choice == QMessageBox.Yes:
            sys.exit()
        else:
            pass

    def import_sqlite_database(self):
        zip_filter = 'zip files (*.zip)'
        # zip_name = QFileDialog.getOpenFileName(self, 'Import sqlite database', str(Path.home()), zip_filter)
        zip_name = QFileDialog.getOpenFileName(self, 'Import sqlite database', 'C:\data\openlca\zip', zip_filter)
        if zip_name[0] == '':
            return
        db_output_path = self.system['data_path'].joinpath(Path(zip_name[0]).with_suffix('.sqlite').name)
        if db_output_path.exists():
            QMessageBox.critical(self, 'Error', 'Database already exists', QMessageBox.Ok)
        else:
            try:
                print('Uncompressing', zip_name[0], 'to', self.system['data_path'])
                with ZipFile(zip_name[0], 'r') as zr:
                    zr.extractall(self.system['data_path'])
                self.manager.add_database(db_output_path)
            except Exception as e:
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
        # TODO this should really go into manager class
        if len(self.manager.db_items) > 0:
            dialog = md.NewModelDialog(parent=self, db_files=self.manager.db_items.keys())
            if dialog.exec():
                name, specification_class, controller_class, database, doc_file = dialog.get_inputs()
                config_file = self.system['config_path'].joinpath(name + '.json')
                if config_file.exists():
                    QMessageBox.about(self, "Error", "Configuration file " + str(config_file.absolute()) +
                                      " already exists")
                else:
                    if database:
                        item = QTreeWidgetItem(self.manager.db_items[database], [config_file.stem])
                    else:
                        item = QTreeWidgetItem(self.manager.db_items['None'], [config_file.stem])
                    self.manager.db_tree.clearSelection()
                    item.setSelected(True)
                    self.manager.new_model(config_file, specification_class, controller_class, database, doc_file)
                    self.save_model()

    def save_model(self):
        try:
            if isinstance(self.manager.controller, mc.Controller):
                # TODO this should go into the Controller/Manager class
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

    def _create_toolbars(self):
        main_tool_bar = self.addToolBar("Main")
        main_tool_bar.setIconSize(QSize(24, 24))
        main_tool_bar.addAction(self.new_model_action)
        main_tool_bar.addAction(self.save_model_action)
        main_tool_bar.addAction(self.open_db_action)
        main_tool_bar.addAction(self.about_action)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = MolaMainWindow()
    app.aboutToQuit.connect(gui.shutdown_kernel)
    sys.exit(app.exec_())
