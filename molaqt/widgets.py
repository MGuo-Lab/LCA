import webbrowser
from pathlib import Path
from functools import partial

import pandas as pd

from PyQt5.QtCore import Qt, QUrl, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QGridLayout, QTableView, QHeaderView, QLineEdit, QDialog, \
    QAbstractItemView, QComboBox, QDialogButtonBox, QPushButton, QWidget, QListWidget, QAction, QLabel, QInputDialog,\
    QVBoxLayout, QSlider, QCheckBox, QApplication, QHBoxLayout, QMessageBox, QSplitter, QTreeWidgetItemIterator, \
    QSizePolicy
from PyQt5.QtWebEngineWidgets import QWebEngineView
from pyvis.network import Network
from tempfile import NamedTemporaryFile

import molaqt.datamodel as md
import mola.build as mb
import mola.utils as mu
import mola.dataview as mdv
import molaqt.utils as mqu


class ImageWidget(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        # self.setScaledContents(True)

    def hasHeightForWidth(self):
        return self.pixmap() is not None

    def heightForWidth(self, w):
        if self.pixmap():
            return int(w * (self.parent.height() / self.parent.width()))


class LookupWidget(QDialog):

    def __init__(self, lookup, set_name, set_label=None):

        super().__init__()
        if set_label is None:
            set_label = set_name
        self.setWindowTitle('Lookup ' + set_label)
        self.resize(800, 600)
        self.setWindowIcon(QIcon('resources/python-logo.png'))

        # self.lookup = lookup
        # self.set_name = set_name
        self.df = lookup.get(set_name)
        self.chunk_size = 10

        # more button
        more_button = QPushButton('More')
        more_button.clicked.connect(self.more_clicked)

        # ok and cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # data model
        self.chunked_iter = mqu.chunker(self.df, self.chunk_size)
        self.chunked_df = next(self.chunked_iter, pd.DataFrame())
        self.lookup_model = md.PandasModel(self.chunked_df, is_indexed=True)

        # live search on lookup
        live_search = QLineEdit()
        live_search.textChanged.connect(self.text_changed)

        # lookup table
        self.lookup_table = QTableView()
        self.lookup_table.setModel(self.lookup_model)
        self.lookup_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.lookup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.lookup_table.setSelectionBehavior(QTableView.SelectRows)

        # arrange widgets in grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(live_search, 0, 0)
        grid_layout.addWidget(more_button, 0, 1)
        grid_layout.addWidget(buttons, 0, 2)
        grid_layout.addWidget(self.lookup_table, 1, 0, 1, 3)
        self.setLayout(grid_layout)

    def more_clicked(self):
        df = next(self.chunked_iter, pd.DataFrame())
        self.chunked_df = self.chunked_df.append(df)
        self.lookup_model = md.PandasModel(self.chunked_df, is_indexed=True)
        self.lookup_table.setModel(self.lookup_model)

    def text_changed(self, text):
        first_col = self.df.iloc[:, 0]
        filtered_df = self.df.loc[first_col.str.contains(text, case=False, regex=False), :]
        if len(filtered_df) > 0:
            self.chunked_iter = mqu.chunker(filtered_df, self.chunk_size)
            self.chunked_df = next(self.chunked_iter)
            self.lookup_model = md.PandasModel(self.chunked_df, is_indexed=True)
            self.lookup_table.setModel(self.lookup_model)
            self.lookup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        else:
            self.chunked_iter = iter(())
            self.chunked_df = pd.DataFrame()
            self.lookup_model = md.PandasModel(self.chunked_df)
            self.lookup_table.setModel(self.lookup_model)

    def get_elements(self):
        """
        Get the ref ids from selected rows in table.

        :return: List of reference ids
        """
        idx = self.lookup_table.selectedIndexes()
        rows = list(set([i.row() for i in idx]))
        ref_ids = self.chunked_df.index[rows].to_list()
        return ref_ids


class SetsEditor(QWidget):

    def __init__(self, sets, spec, lookup):
        """
        Widget to edit optimisation sets.

        :param list user_sets: sets modified in place by this widget
        :param Specification spec: object
        :param LookupTables lookup: object
        """

        super().__init__()
        self.sets = sets
        self.spec = spec
        self.lookup = lookup

        # merge user set into spec defaults
        # sets = spec.get_default_sets()
        # sets.update(user_sets)

        # only allow user-defined sets to be changed
        user_defined_sets = {k: sets[k] for k in spec.user_defined_sets.keys()}

        # flag to indicate data changes
        self.dirty = False

        # add list widget for user-defined sets
        self.sets_list = QListWidget()
        self.sets = sets
        self.user_defined_sets = user_defined_sets
        self.sets_list.addItems(self.user_defined_sets)
        self.sets_list.itemClicked.connect(self.set_clicked)
        self.sets_list.setCurrentItem(self.sets_list.item(0))

        # add table for set content
        self.set_table = QTableView()
        first_set = next(iter(self.user_defined_sets))
        set_model = self.get_model(first_set)
        self.set_table.setModel(set_model)
        self.set_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.remove_action = QAction("Remove from set", None)
        self.remove_action.triggered.connect(self.remove_from_set)
        self.set_table.addAction(self.remove_action)
        self.set_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        # button
        self.add_element_button = QPushButton("Add new element")
        self.add_element_button.clicked.connect(self.add_element_clicked)

        # arrange widgets in grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("Sets"), 0, 0)
        grid_layout.addWidget(self.sets_list, 1, 0, 2, 1)
        self.set_label = QLabel(first_set + ': ' + spec.user_defined_sets[first_set])
        grid_layout.addWidget(self.set_label, 0, 1)
        grid_layout.addWidget(self.add_element_button, 0, 2)
        grid_layout.addWidget(self.set_table, 1, 1, 1, 2)
        grid_layout.setColumnStretch(1, 2)
        self.setLayout(grid_layout)

    def add_element_clicked(self):
        current_set = self.sets_list.currentItem().text()
        if current_set not in self.lookup.keys():
            text, ok = QInputDialog.getText(self, 'Add Element', 'Name:')
            if ok:
                self.sets[current_set].append(str(text))
                self.set_table.setModel(md.SetModel(self.sets[current_set]))
                self.dirty = True
                print("Added element", text)
        else:
            # QMessageBox.about(self, "Error", "Use lookup for this set")
            lookup_widget = LookupWidget(self.lookup, current_set)
            ok = lookup_widget.exec_()
            if ok:
                ref_ids = lookup_widget.get_elements()
                self.sets[current_set].extend(ref_ids)
                df = self.lookup.get(current_set, self.sets[current_set])
                self.set_table.setModel(md.PandasModel(df, is_indexed=True))
                self.dirty = True
                print('Added to set', ref_ids)

    # def add_to_set(self):
    #     current_set = self.sets_list.currentItem().text()
    #     # get the unfiltered row numbers
    #     rows = [self.filter_lookup_model.mapToSource(i).row() for i in self.lookup_table.selectedIndexes()]
    #     self.sets[current_set] += self.lookup[current_set].index[rows].to_list()
    #     df = self.lookup[current_set].loc[self.sets[current_set], :]
    #     self.set_table.setModel(md.PandasModel(df, is_indexed=True))
    #     self.dirty = True
    #     print('Added to set', rows)

    def remove_from_set(self):
        current_set = self.sets_list.currentItem().text()
        rows = [i.row() for i in self.set_table.selectedIndexes()]
        model = self.set_table.model()
        ref_ids = model._data.index[rows].to_list()
        for ref in ref_ids:
            if ref in self.sets[current_set]:
                self.sets[current_set].remove(ref)
        if current_set in self.lookup.keys():
            df = self.lookup.get(current_set, self.sets[current_set])
            model = md.PandasModel(df, is_indexed=True)
        else:
            model = md.SetModel(self.sets[current_set])
        self.dirty = True
        self.set_table.setModel(model)
        print('Removed from set', rows)

    def set_clicked(self, item):
        user_set = item.text()
        print("Clicked set list with", user_set)
        self.set_label.setText(user_set + ': ' + self.spec.user_defined_sets[user_set])
        model = self.get_model(user_set)
        self.set_table.setModel(model)

    def get_model(self, set_name):
        if set_name in self.lookup.keys():
            set_dfr = self.lookup.get(set_name, self.sets[set_name])
            model = md.PandasModel(set_dfr, is_indexed=True)
        else:
            model = md.SetModel(self.sets[set_name])

        return model


class DocWidget(QWidget):

    def __init__(self, doc_path):

        super().__init__()

        # html content
        self.documentation = QWebEngineView()
        url = QUrl.fromLocalFile(str(doc_path))
        self.documentation.load(url)
        self.documentation.setZoomFactor(1.0)

        # zoom slider
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setMinimum(25)
        self.zoom.setMaximum(500)
        self.zoom.setValue(100)
        self.zoom.setTickPosition(QSlider.TicksBelow)
        self.zoom.setTickInterval(25)
        self.zoom.valueChanged.connect(self.zoom_change)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.zoom)
        layout.addWidget(self.documentation)
        self.setLayout(layout)

    def zoom_change(self):
        size = self.zoom.value()
        self.documentation.page().setZoomFactor(size / 100)


class ParametersEditor(QWidget):

    def __init__(self, sets, parameters, spec, lookup):
        """
        Widget to modify a copy of the parameters list. Use the get_parameters method to obtain an
        up-to-date copy.

        :param list sets: optimisation sets
        :param list parameters: optimisation parameters
        :param Specification spec: object
        :param LookupTables lookup: object
        """

        super().__init__()
        self.spec = spec
        self.sets = sets
        self.lookup = lookup

        # build a dictionary of DataFrames of default parameters from sets
        # self.par = {k: v for k, v in mb.build_parameters(sets, parameters, spec).items() if k in parameters}
        self.par = mb.build_parameters(sets, parameters, spec)

        # list widget for user-defined parameters
        self.parameters_list = QListWidget()
        self.parameter_names = parameters.keys()
        self.parameters_list.addItems(self.parameter_names)
        self.parameters_list.itemClicked.connect(self.parameter_clicked)
        self.parameters_list.setCurrentItem(self.parameters_list.item(0))

        # parameter widget
        parameter_name = next(iter(self.par))
        self.parameter_widget = QLabel()

        # rebuild button
        self.rebuild_button = QPushButton("Rebuild")
        self.rebuild_button.clicked.connect(self.rebuild_clicked)

        # arrange widgets in grid
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(QLabel("Parameters"), 0, 0)
        self.grid_layout.addWidget(self.rebuild_button, 0, 1)
        self.grid_layout.addWidget(self.parameters_list, 1, 0, 1, 2)
        self.grid_layout.addWidget(self.parameter_widget, 0, 2, 2, 1)
        self.grid_layout.setColumnStretch(2, 20)
        self.setLayout(self.grid_layout)

        # set default parameter
        self.set_parameter_widget(parameter_name)

    def parameter_clicked(self, item):
        param = item.text()
        print("Clicked parameter list with", param)
        self.set_parameter_widget(param)

    def set_parameter_widget(self, param):
        self.parameter_widget.close()
        if 'within' in self.spec.user_defined_parameters[param] and param in self.par:
            new_parameter_widget = LinkingParameterWidget(param, self.par[param], self.spec, self.lookup)
        elif param in self.par:
            new_parameter_widget = ParameterWidget(param, self.par[param], self.spec, self.lookup)
        else:
            new_parameter_widget = QLabel('Not available')
        self.grid_layout.replaceWidget(self.parameter_widget, new_parameter_widget)
        self.parameter_widget = new_parameter_widget
        self.grid_layout.update()

    def rebuild_clicked(self):
        print("Clicked rebuild button")
        p = self.get_parameters()
        # TODO fix the logic here
        # self.par = {k: v for k, v in mb.build_parameters(self.sets, p, self.spec).items() if k in p}
        self.par = mb.build_parameters(self.sets, p, self.spec)
        self.parameter_clicked(self.parameters_list.selectedItems()[0])

    def get_parameters(self):
        """Turn dict of dataframes into a dict of lists of index value dicts"""
        param = {p: list(df.apply(lambda g: {'index': g[0], 'value': g[1]}, axis=1))
                 for p, df in self.par.items() if len(df) > 0}
        return param


class ParameterWidget(QWidget):

    def __init__(self, name, table, spec, lookup):

        super().__init__()

        # parameter label
        if 'unit' in spec.user_defined_parameters[name]:
            unit = spec.user_defined_parameters[name]['unit']
        else:
            unit = 'None'
        param_doc_str = name + ': ' + spec.user_defined_parameters[name]['doc'] + ', ' + \
            'Unit: ' + str(unit)
        param_doc_label = QLabel(param_doc_str)

        # table of parameters
        self.parameter_table = QTableView()
        index_sets = spec.user_defined_parameters[name]['index']
        self.parameter_table.setModel(md.ParameterModel(table, index_sets, lookup))
        self.parameter_table.setColumnHidden(0, True)
        self.parameter_table.resizeColumnsToContents()

        # arrange widgets
        layout = QVBoxLayout()
        layout.addWidget(param_doc_label)
        layout.addWidget(self.parameter_table)
        self.setLayout(layout)


class LinkingParameterWidget(QWidget):

    def __init__(self, name, table, spec, lookup):

        super().__init__()
        self.name = name
        self.table = table
        self.spec = spec
        self.lookup = lookup

        # parameter label
        param_doc_str = name + ': ' + spec.user_defined_parameters[name]['doc'] + ' (Linking)'
        param_doc_label = QLabel(param_doc_str)

        # table of parameters (affects table!)
        self.parameter_table = QTableView()
        index_sets = self.spec.user_defined_parameters[name]['index']
        self.parameter_table.setModel(md.ParameterModel(table, index_sets, lookup))
        self.parameter_table.setColumnHidden(0, True)

        # dict to map link number to table row in sets enumeration
        link_row = table[table['Value'] == 1]
        self.link = {str(i): row for i, row in enumerate(link_row.index)}

        # link combobox
        self.link_combobox = QComboBox()
        self.link_combobox.addItems(self.link.keys())
        self.link_combobox.currentIndexChanged.connect(self.link_changed)

        # buttons
        self.add_link = QPushButton('Add link')
        self.remove_link = QPushButton('Remove link')
        self.visualise = QPushButton('Visualise')
        self.add_link.clicked.connect(self.add_link_clicked)
        self.remove_link.clicked.connect(self.remove_link_clicked)
        self.visualise.clicked.connect(self.visualise_clicked)

        # set dropdowns
        set_layout = QGridLayout()
        self.set_combobox = dict()
        for i, index in enumerate(spec.user_defined_parameters[name]['index']):
            self.set_combobox[index] = QComboBox()
            self.set_combobox[index].addItems(table[index].unique())
            set_layout.addWidget(QLabel(index + ": "), i, 0)
            set_layout.addWidget(self.set_combobox[index], i, 1)
        set_layout.setColumnStretch(1, 2)

        # set dropdown to first link if there is one
        if len(self.link) > 0:
            self.link_changed(0)

        # arrange widgets
        grid_layout = QGridLayout()
        grid_layout.addWidget(param_doc_label, 0, 0, 1, 4)
        grid_layout.addWidget(QLabel('Link Number: '), 1, 0)
        grid_layout.addWidget(self.link_combobox, 1, 1)
        grid_layout.addWidget(self.add_link, 1, 2)
        grid_layout.addWidget(self.remove_link, 1, 3)
        grid_layout.addWidget(self.visualise, 1, 4)
        grid_layout.addLayout(set_layout, 2, 0, 1, 5)
        grid_layout.addWidget(self.parameter_table, 3, 0, 1, 5)
        grid_layout.setColumnStretch(1, 2)
        grid_layout.setColumnStretch(2, 2)
        grid_layout.setColumnStretch(3, 2)
        grid_layout.setColumnStretch(4, 2)
        self.setLayout(grid_layout)

    def link_changed(self, index):
        if len(self.link) > 0:
            link_key = list(self.link.keys())[index]
            # get the ref ids from table for link_num
            table_row_num = self.link[link_key]
            link_row = self.table.loc[table_row_num]
            link_ref_ids = self.table['Index'][table_row_num]
            print('Link', link_key, ':', link_row)

            # set text from ref id lookup for each combobox
            for ref_id, set_name in zip(link_ref_ids, self.spec.user_defined_parameters[self.name]['index']):
                ref_id_text = self.lookup.get_single_column(set_name, ref_id)[0]
                index = self.set_combobox[set_name].findText(ref_id_text, Qt.MatchFixedString)
                if index >= 0:
                    self.set_combobox[set_name].setCurrentIndex(index)
                    self.parameter_table.selectRow(table_row_num)

    def add_link_clicked(self):
        # the new link number is the last in self.link+1 or 0
        if len(self.link) > 0:
            last_link_num = list(self.link)[-1]
            new_link_num = int(last_link_num) + 1
        else:
            new_link_num = 0

        # get the combobox selections
        selected_item = {set_name: cb.currentText() for set_name, cb in self.set_combobox.items()}
        df = self.table[selected_item.keys()]

        # update table
        row_match = (df == pd.Series(selected_item)).all(1)
        if len(row_match) > 0:
            table_row = row_match.index[row_match][0]
            if self.table.at[table_row, 'Value'] == 1:
                self.parameter_table.selectRow(table_row)
                QMessageBox.information(self, 'Link already exists', "Choose another set combination", QMessageBox.Ok)
            else:
                print('Adding new link at table row', table_row)
                self.table.at[table_row, 'Value'] = 1
                self.link[str(new_link_num)] = table_row
                self.link_combobox.addItem(str(new_link_num))
                self.link_combobox.setCurrentIndex(new_link_num)

    def remove_link_clicked(self):
        index = self.link_combobox.currentIndex()
        if index >= 0:
            link_key = list(self.link.keys())[index]
            print('removing link', link_key)
            self.table.at[self.link[link_key], 'Value'] = 0
            del self.link[link_key]
            self.link_combobox.removeItem(index)  # this calls link_changed

    def visualise_clicked(self):
        print('visualising links')
        index_sets = self.spec.user_defined_parameters[self.name]['index']
        parameter_diagram = LinkParameterDiagram(self.table, index_sets, self.lookup)
        html_path = parameter_diagram.get_html_path()
        url = html_path.resolve().as_uri()
        webbrowser.open(url, new=2) # new tab


class AboutWidget(QWidget):

    def __init__(self, settings):
        super().__init__()
        self.setWindowTitle("MolaQT: Mathematical Optimisation of Lifecycle Assessment Models")

        # widgets
        label = QLabel()
        pixmap = QPixmap(str(settings['package_path'].joinpath(":Sunfish2.jpg")))
        pixmap = pixmap.scaledToWidth(800)
        # painter = QPainter(pixmap)
        # painter.setFont(QFont("Arial"));
        # painter.drawText(QPoint(10, 10), "MolaQT: Mathematical Optimisation of Lifecycle Models")
        label.setPixmap(pixmap)
        label.setScaledContents(True)

        # layout
        layout = QHBoxLayout(self)
        layout.addWidget(label)
        self.setLayout(layout)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        self.show()
        self.center()

    def center(self):
        frame_gm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        center_point = QApplication.desktop().screenGeometry(screen).center()
        frame_gm.moveCenter(center_point)
        self.move(frame_gm.topLeft())
        # self.move(QDesktopWidget().availableGeometry().center().x() - self.frameGeometry().center().x() * 0.5,
        #           QDesktopWidget().availableGeometry().center().y() - self.frameGeometry().center().y() * 0.5)


class ProcessFlow(QWidget):

    def __init__(self, user_sets, user_parameters, spec, lookup, conn):

        super().__init__()
        self.spec = spec
        self.lookup = lookup
        self.conn = conn
        self.is_indexed = True
        self.sets = user_sets
        self.parameters = user_parameters  # in index, value form

        # flag to indicate data changes
        self.dirty = False

        # add tree for processes
        self.process_tree = QTreeWidget()
        self.process_tree.setHeaderLabels(['Type', 'Name', 'Location'])
        self.material_tree = QTreeWidgetItem(self.process_tree, ['Material'])
        self.material_tree.setExpanded(True)
        self.transport_tree = QTreeWidgetItem(self.process_tree, ['Transport'])
        self.transport_tree.setExpanded(True)
        self.process_tree.itemClicked.connect(self.process_tree_clicked)
        self.process_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # add tree widget items for material processes
        material_set_df = self.lookup.get('P_m', self.sets['P_m'])
        material_process = []
        for index, row in material_set_df.iterrows():
            qwi = QTreeWidgetItem(self.material_tree, [index, row.PROCESS_NAME, row.LOCATION_NAME])
            material_process.append(qwi)

        # add tree widget items for transport processes
        transport_set_df = self.lookup.get('P_t', self.sets['P_t'])
        transport_process = []
        for index, row in transport_set_df.iterrows():
            qwi = QTreeWidgetItem(self.transport_tree, [index, row.PROCESS_NAME, row.LOCATION_NAME])
            transport_process.append(qwi)
        self.process_tree.resizeColumnToContents(1)

        # context menu for process tree
        self.process_tree.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.remove_process_action = QAction("Remove process", None)
        self.remove_process_action.triggered.connect(self.remove_process)
        self.process_tree.addAction(self.remove_process_action)

        # add table for flows
        self.flows_table = QTableView()
        flows_model = md.PandasModel(pd.DataFrame(columns=['Input Process ID', 'Input Process Name',
                                                           'Output Flow ID', 'Output Flow Name']))
        self.flows_table.setModel(flows_model)
        self.flows_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.flows_table.resizeRowsToContents()

        # buttons
        self.add_material_process_button = QPushButton("Add Material Process")
        self.add_transport_process_button = QPushButton("Add Transport Process")
        self.link_processes_button = QPushButton("Link Processes")
        self.unlink_processes_button = QPushButton("Unlink Processes")
        self.visualise_button = QPushButton("Visualise")
        self.add_material_process_button.clicked.connect(self.add_material_process_clicked)
        self.add_transport_process_button.clicked.connect(self.add_transport_process_clicked)
        self.link_processes_button.clicked.connect(partial(self.material_transport_link, 1))
        self.unlink_processes_button.clicked.connect(partial(self.material_transport_link, 0))
        self.visualise_button.clicked.connect(self.visualise_material_transport_clicked)

        # labels
        self.flows_label = QLabel("Flows")

        # arrange widgets in grid
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("Processes"), 0, 0)
        grid_layout.addWidget(self.add_material_process_button, 0, 1)
        grid_layout.addWidget(self.add_transport_process_button, 0, 2)
        grid_layout.addWidget(self.link_processes_button, 0, 3)
        grid_layout.addWidget(self.unlink_processes_button, 0, 4)
        grid_layout.addWidget(self.visualise_button, 0, 5)
        grid_layout.addWidget(self.process_tree, 1, 0, 1, 6)
        grid_layout.addWidget(self.flows_label, 2, 0, 1, 6)
        grid_layout.addWidget(self.flows_table, 3, 0, 1, 6)
        grid_layout.setColumnStretch(0, 1)

        self.setLayout(grid_layout)

    def visualise_material_transport_clicked(self):
        param_name = 'J'
        index_sets = self.spec.user_defined_parameters[param_name]['index']
        params = mb.build_parameters(self.sets, self.get_parameters(), self.spec)
        df = pd.DataFrame(params[param_name])
        parameter_diagram = LinkParameterDiagram(df, index_sets, self.lookup)
        html_path = parameter_diagram.get_html_path()
        url = html_path.resolve().as_uri()
        webbrowser.open(url, new=2)  # new tab

    @pyqtSlot(QTreeWidgetItem)
    def process_tree_clicked(self, item):
        if item.parent() is None:
            return
        ref_id = item.text(0)

        # get product flow for selected process
        product_flow_df = mdv.get_process_product_flow(self.conn, ref_id)
        product_flow_df = product_flow_df[['FLOW_REF_ID', 'FLOW_NAME']]
        product_flow_df.columns = ['Output Flow ID', 'Output Flow Name']

        # for transport flows find if there is a connecting material flow
        if item.parent().text(0) == 'Transport':
            if product_flow_df.shape[0] > 0 and 'J' in self.parameters:
                j_link = pd.DataFrame([j['index'] for j in self.parameters['J'] if j['value'] == 1],
                                      columns=['F_m', 'P_m', 'F_t', 'P_t'])
                df = j_link[(j_link.P_t == ref_id) & (j_link.F_t == product_flow_df.iloc[0, 0])]
                if df.shape[0] > 0:
                    # fm_ref_id = df['F_m'].iloc[0]
                    pm_ref_id = df['P_m'].iloc[0]
                    # fm_lookup = self.lookup.get('F_m', fm_ref_id)
                    pm_lookup = self.lookup.get('P_m', pm_ref_id)
                    product_flow_df.insert(0, 'Input Process Name', pm_lookup.iloc[0] + pm_lookup.iloc[1])
                    product_flow_df.insert(0, 'Input Process ID', pm_ref_id)
                    # product_flow_df.insert(0, 'Input Flow Name', fm_lookup)
                    # product_flow_df.insert(0, 'Input Flow ID', fm_ref_id)
                else:
                    product_flow_df.insert(0, 'Input Process Name', '')
                    product_flow_df.insert(0, 'Input Process ID', '')
            else:
                product_flow_df = pd.DataFrame()
        else:
            product_flow_df.insert(0, 'Input Process Name', '')
            product_flow_df.insert(0, 'Input Process ID', '')

        flows_model = md.PandasModel(product_flow_df, is_indexed=False)
        self.flows_table.setModel(flows_model)
        self.flows_table.resizeRowsToContents()

    def add_material_process_clicked(self):
        print('Add material process button clicked')
        lookup_widget = LookupWidget(self.lookup, 'P_m', "Material Process")
        ok = lookup_widget.exec()
        if ok:
            process_ids = lookup_widget.get_elements()
            new_processes = [pid for pid in process_ids if pid not in self.sets['P_m']]
            if len(new_processes) > 0:
                # add the new process ref ids to the material set and update tree
                self.sets['P_m'].extend(new_processes)
                df = self.lookup.get('P_m', new_processes)
                for index, row in df.iterrows():
                    self.material_tree.addChild(
                        QTreeWidgetItem(self.material_tree, [index, row['PROCESS_NAME'], row['LOCATION_NAME']])
                    )
                self.dirty = True
                print('Added material process', new_processes)

                # add new product flows to set and update parameters
                product_flow_df = mdv.get_process_product_flow(self.conn, new_processes)
                flow_ids = list(product_flow_df.FLOW_REF_ID.unique())
                if len(flow_ids) > 0:
                    self.sets['F_m'].extend([fid for fid in flow_ids if fid not in self.sets['F_m']])
                params = mb.build_parameters(self.sets, self.get_parameters(), self.spec)
                self.parameters = mu.get_index_value_parameters(params)
                self.process_tree.resizeColumnToContents(1)

    def remove_process(self):
        items = self.process_tree.selectedItems()
        for item in items:
            parent = item.parent()
            if parent is None:
                continue
            ref_id = item.text(0)
            if parent.text(0) == 'Material':
                self.sets['P_m'].remove(ref_id)
                for i in range(self.material_tree.childCount()):
                    if self.material_tree.child(i).text(0) == ref_id:
                        self.material_tree.takeChild(i)
                        break
                print('Removed ', ref_id)
                # ensure only relevant product flows are in F_m
                product_flow_df = mdv.get_process_product_flow(self.conn, self.sets['P_m'])
                flow_ids = product_flow_df.FLOW_REF_ID.to_list()
                for fid in self.sets['F_m']:
                    if fid not in flow_ids:
                        self.sets['F_m'].remove(fid)
            elif parent.text(0) == 'Transport':
                self.sets['P_t'].remove(ref_id)
                for i in range(self.transport_tree.childCount()):
                    if self.transport_tree.child(i).text(0) == ref_id:
                        self.transport_tree.takeChild(i)
                        break
                print('Removed ', ref_id)
                # ensure only relevant product flows are in F_t
                product_flow_df = mdv.get_process_product_flow(self.conn, self.sets['P_t'])
                flow_ids = product_flow_df.FLOW_REF_ID.to_list()
                for fid in self.sets['F_t']:
                    if fid not in flow_ids:
                        self.sets['F_t'].remove(fid)

        # rebuild sets and parameters
        params = mb.build_parameters(self.sets, self.get_parameters(), self.spec)
        self.parameters = mu.get_index_value_parameters(params)
        self.process_tree.resizeColumnToContents(1)

    def add_transport_process_clicked(self):
        print('Add transport process button clicked')
        lookup_widget = LookupWidget(self.lookup, 'P_t', "Transport Process")
        ok = lookup_widget.exec()
        if ok:
            process_ids = lookup_widget.get_elements()
            new_processes = [pid for pid in process_ids if pid not in self.sets['P_t']]
            if len(new_processes) > 0:
                # add the new process ref ids to the material set and update tree
                self.sets['P_t'].extend(new_processes)
                df = self.lookup.get('P_t', new_processes)
                for index, row in df.iterrows():
                    self.material_tree.addChild(
                        QTreeWidgetItem(self.transport_tree, [index, row['PROCESS_NAME'], row['LOCATION_NAME']])
                    )
                self.dirty = True
                print('Added transport process', new_processes)

                # add new product flows to set and update parameters
                product_flow_df = mdv.get_process_product_flow(self.conn, new_processes)
                flow_ids = list(product_flow_df.FLOW_REF_ID.unique())
                if len(flow_ids) > 0:
                    self.sets['F_t'].extend([fid for fid in flow_ids if fid not in self.sets['F_t']])
                params = mb.build_parameters(self.sets, self.get_parameters(), self.spec)
                self.parameters = mu.get_index_value_parameters(params)
                self.process_tree.resizeColumnToContents(1)

    def material_transport_link(self, link: bool):
        item = self.process_tree.selectedItems()
        if len(item) != 2 or item[0].parent() is None or item[1].parent() is None or \
                item[0].parent().text(0) == item[1].parent().text(0):
            return
        m = int(item[0].parent().text(0) == "Transport")  # the material item
        pm = item[m].text(0)
        pt = item[1-m].text(0)

        # get the product flows for the processes
        product_flow_df = mdv.get_process_product_flow(self.conn, pm)
        if product_flow_df.shape[0] > 0:
            fm = product_flow_df.FLOW_REF_ID.iloc[0]
        else:
            fm = None
        product_flow_df = mdv.get_process_product_flow(self.conn, pt)
        if product_flow_df.shape[0] > 0:
            ft = product_flow_df.FLOW_REF_ID.iloc[0]
        else:
            ft = None

        # link processes and flows
        for i, j in enumerate(self.parameters['J']):
            if j['index'] == [fm, pm, ft, pt]:
                print(i, j['index'])
                self.parameters['J'][i] = {'index': j['index'], 'value': link}

        # update display
        self.process_tree_clicked(item[1-m])

    # def get_new_j(self, ref_ids, parameter_j):
    #     # create a new link table for every F_t, P_t combination for each ref_id
    #     link = pd.DataFrame([j['index'] for j in parameter_j if j['value'] == 1],
    #                         columns=['F_m', 'P_m', 'F_t', 'P_t'])
    #     transport_df = link[['F_t', 'P_t']].drop_duplicates()
    #     new_link = pd.concat([transport_df] * len(ref_ids))
    #     new_link.insert(0, 'P_m', [ref_ids] * new_link.shape[0])
    #     new_link.insert(0, 'F_m', '')
    #     new_link['value'] = 1
    #
    #     # put sets into one column
    #     new_link['index'] = new_link[['F_m', 'P_m', 'F_t', 'P_t']].values.tolist()
    #     df = new_link[['index', 'value']]
    #
    #     # turn table into json format
    #     def f(g): return {'index': g[0], 'value': g[1]}
    #     new_j = list(df.apply(f, axis=1))
    #
    #     return new_j

    def get_parameters(self):
        return self.parameters


class ConfigurationWidget(QWidget):

    def __init__(self, spec):

        super().__init__()

        self.spec = spec

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # use the default specification settings to construct the widgets
        self.widget = {}
        for k, v in self.spec.default_settings.items():
            if v['type'] == 'boolean':
                self.widget[k] = QCheckBox(v['doc'])
                self.widget[k].setChecked(self.spec.settings[k])
                self.widget[k].stateChanged.connect(lambda: self.boolean_state(self.widget[k], k))
                layout.addWidget(self.widget[k])

        self.setLayout(layout)

    def boolean_state(self, bw, setting):
        self.spec.settings[setting] = bw.isChecked()


class LinkParameterDiagram:

    def __init__(self, table, index_sets, lookup, node_lookup='P'):
        """
        Generates HTML pyvis charts that visualise the connections represented by a linking parameter.

        Assumes product flows are odd sets and processes are even sets in the ordering of the
        linking parameter.

        :param DataFrame table: the link parameter enumeration table
        :param list index_sets: names of set that index the parameter
        :param LookupTables lookup: cache of lookup tables
        :param str node_lookup: name of set which denotes nodes
        """

        self.table = table
        self.index_sets = index_sets
        self.node_sets = index_sets[1::2]
        self.edge_sets = index_sets[0::2]

        # bring the index into the DataFrame
        df = pd.DataFrame(table["Index"].to_list(), columns=index_sets)

        # nodes
        self.g = Network(width='100%', height=800, heading='Link Parameter Diagram')
        # self.g.show_buttons()
        nodes = [ref_id for n in self.node_sets for ref_id in df[n].unique()]
        titles = lookup.get_single_column(node_lookup, nodes)[node_lookup]
        titles = [t.replace('|', '\n') for t in titles]
        colors = ['#FF9999' if n in df['P_m'].unique() else '#9999FF' for n in nodes]
        levels = [i for i, n in enumerate(self.node_sets) for ref_id in df[n].unique()]
        nodes += ['output']
        titles += ['output']
        colors += ['black']
        levels += [2]
        for i in range(len(nodes)):
            self.g.add_node(nodes[i], title=nodes[i], label=titles[i], color=colors[i], level=levels[i], mass=2)
        self.g.set_options("""
        var options = {
          "edges": {
            "color": {
              "inherit": true
            },
            "smooth": false
          },
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "LR",
              "levelSeparation": 300
            }
          },
          "physics": {
            "enabled": false,
            "hierarchicalRepulsion": {
              "centralGravity": 0
            },
            "minVelocity": 0.75,
            "solver": "hierarchicalRepulsion"
          }
        }
        """)

        # HTML widget
        self.viewer = QWebEngineView()
        # edges between node sets
        edge_boundary = self.node_sets + ['output']
        for index, row in self.table.iterrows():
            if row['Value']:
                row_index = {s: row['Index'][i] for i, s in enumerate(self.index_sets)}
                for i, (a, b) in enumerate(zip(edge_boundary, edge_boundary[1:])):
                    if b == 'output':
                        self.g.add_edge(row_index[a], 'output', title=row_index[self.edge_sets[i]])
                    else:
                        self.g.add_edge(row_index[a], row_index[b], title=row_index[self.edge_sets[i]])

        # layout
        # layout = QVBoxLayout(self)
        # layout.setContentsMargins(0, 0, 0, 0)
        # layout.addWidget(self.viewer)
        # self.setLayout(layout)

    def get_html_path(self):
        # write html to temp file
        temp_html = NamedTemporaryFile(suffix='.html', delete=False)
        self.g.write_html(temp_html.name)
        temp_html.close()
        # url = QUrl.fromLocalFile(temp_html.name)
        # self.viewer.load(url)
        # self.viewer.setZoomFactor(1.0)

        return Path(temp_html.name)


class ObjectiveWidget(QWidget):

    def __init__(self, lookup, kpi_set):
        """
        QWidget to choose the environmental impact category.

        :param LookupTables lookup: cache of tables
        :param list kpi_set: kpi references modified in place by this object
        """
        super().__init__()
        self.kpi_set = kpi_set
        self.dirty = False

        self.setWindowTitle("Select Objective")

        # method tree
        self.method_tree = QTreeWidget()
        self.method_tree.setHeaderLabels(['Impact Category', 'Reference Unit', 'ID'])
        self.method_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.method_tree.itemDoubleClicked.connect(self.add_category)

        # add methods and categories to method tree
        self.lookup_df = lookup.get('KPI')
        methods = {}
        for method in self.lookup_df['Method'].unique():
            if '(obsolete)' not in method:
                methods[method] = QTreeWidgetItem(self.method_tree, [method])
        for index, row in self.lookup_df.iterrows():
            if row['Method'] in methods.keys():
                QTreeWidgetItem(methods[row['Method']], [row['Category'], row['Unit'], index])

        # objective tree
        self.objective_tree = QTreeWidget()
        self.objective_tree.setHeaderLabels(['Impact Category', 'Reference Unit', 'ID'])
        self.objective_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.objective_tree.itemDoubleClicked.connect(self.remove_category)
        self.refresh_objective_tree(kpi_set)

        # layout
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.method_tree)
        self.splitter.addWidget(self.objective_tree)
        method_label = QLabel('Database')
        method_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        objective_label = QLabel('Minimise')
        objective_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QGridLayout()
        layout.addWidget(method_label, 0, 0)
        layout.addWidget(objective_label, 0, 1)
        layout.addWidget(self.splitter, 1, 0, 1, 2)
        self.setLayout(layout)

    def add_category(self, item):
        if self.method_tree.indexOfTopLevelItem(item) == -1:
            ref_id = item.text(2)
            if ref_id not in self.kpi_set:
                if len(self.kpi_set) > 0:
                    self.kpi_set.pop()
                self.kpi_set.append(ref_id)  # in place replace
                # self.kpi_set.append(ref_id) TODO: only allow one kpi for now
                self.refresh_objective_tree(self.kpi_set)
                print('Added to set', ref_id)

    def remove_category(self, item):
        if self.objective_tree.indexOfTopLevelItem(item) == -1:
            ref_id = item.text(2)
            self.kpi_set.remove(ref_id)
            self.refresh_objective_tree(self.kpi_set)
            print('Removed from set', ref_id)

    def refresh_objective_tree(self, kpi_set):
        self.objective_tree.clear()
        objective_df = self.lookup_df.loc[kpi_set]
        objective_methods = {}
        for method in objective_df['Method'].unique():
            objective_methods[method] = QTreeWidgetItem(self.objective_tree, [method])
            objective_methods[method].setExpanded(True)
        for index, row in objective_df.iterrows():
            if row['Method'] in objective_methods.keys():
                QTreeWidgetItem(objective_methods[row['Method']], [row['Category'], row['Unit'], index])

