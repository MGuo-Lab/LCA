from PyQt5.QtCore import QAbstractTableModel, Qt
import pandas as pd


class PandasModel(QAbstractTableModel):

    def __init__(self, data, is_indexed=False):
        QAbstractTableModel.__init__(self)
        self._data = data
        self.is_indexed = is_indexed

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, rowcol, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and len(self._data.columns) > 0:
            return self._data.columns[rowcol]
        if self.is_indexed and orientation == Qt.Vertical and role == Qt.DisplayRole and len(self._data.index) > 0:
            return self._data.index[rowcol]
        return None


class ParameterModel(QAbstractTableModel):

    def __init__(self, data, index_sets, lookup, spec):
        QAbstractTableModel.__init__(self)
        data[index_sets] = pd.DataFrame(data["Index"].to_list(), columns=index_sets)
        lookup_sets = [n for n, d in spec.user_defined_sets.items() if 'lookup' in d and d['lookup']]
        for k in index_sets:
            if k in lookup_sets and k in lookup:
                data[k] = data[k].map(lookup.get_single_column(k)[k])
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.EditRole):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def setData(self, index, value, role):
        if index.isValid() and role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = float(value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        if self._data.columns[index.column()] == 'Value':
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, rowcol, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and len(self._data.columns) > 0:
            return self._data.columns[rowcol]
        if orientation == Qt.Vertical and role == Qt.DisplayRole and len(self._data.index) > 0:
            return self._data.index[rowcol]
        return None


class SetModel(QAbstractTableModel):

    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return 1

    def data(self, index, role=Qt.EditRole):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole:
                return str(self._data[index.row()])
        return None

    def setData(self, index, value, role):
        if index.isValid() and role == Qt.EditRole:
            self._data[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, rowcol, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return "NAME"
        return None

