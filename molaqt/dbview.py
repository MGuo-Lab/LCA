import sys
from PyQt5.QtWidgets import QApplication, QTableView, QComboBox, QMainWindow, QPushButton, QLabel
from PyQt5.QtCore import QAbstractTableModel, Qt
from PyQt5.QtGui import QIcon
import mola.dataimport as di
import mola.dataview as dv
import molaqt.datamodel as md

# We could rewrite this to use Qt functionality for dbs - but it ties database to widget set
# from PyQt5.QtSql import QSqlDatabase, QSqlQueryModel, QSqlTableModel


class DbView(QMainWindow):

    def __init__(self, db_name):

        super(DbView, self).__init__()
        self.setGeometry(50, 50, 800, 600)
        self.setWindowTitle("Database " + db_name)
        self.setWindowIcon(QIcon('images/python-logo.png'))
        self.statusBar()

        # get first table
        self.conn = di.get_sqlite_connection(db_name)
        self.chunk_size = 10
        db_tables = dv.get_table_names(self.conn)
        data = dv.get_table(self.conn, db_tables[0], chunk_size=self.chunk_size)
        self.data_iterator = iter(data)
        self.df = next(self.data_iterator)

        # add a combobox to a toolbar
        combo_box = QComboBox()
        combo_box.insertItems(1, db_tables)
        combo_box.activated[str].connect(self.table_changed)

        # add a more button
        more_button = QPushButton("More")
        more_button.clicked.connect(self.more_clicked)

        # add a toolbar
        self.toolBar = self.addToolBar("table")
        self.toolBar.addWidget(QLabel("Table: "))
        self.toolBar.addWidget(combo_box)
        self.toolBar.addWidget(more_button)

        # add a TableView
        self.table_view = QTableView(self)
        model = md.PandasModel(self.df)
        self.table_view.setModel(model)
        self.setCentralWidget(self.table_view)

        self.show()

    def more_clicked(self):
        self.df = self.df.append(next(self.data_iterator))
        model = md.PandasModel(self.df)
        self.table_view.setModel(model)

    def table_changed(self, table_name):
        print(table_name)
        self.data_iterator = iter(dv.get_table(self.conn, table_name, chunk_size=self.chunk_size))
        self.df = next(self.data_iterator)
        model = md.PandasModel(self.df)
        self.table_view.setModel(model)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    GUI = DbView(di.get_default_db_file())
    sys.exit(app.exec_())
