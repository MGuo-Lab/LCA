from PyQt5.QtCore import QAbstractTableModel, Qt

import molaqt.utils as mqu


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


class SimpleParameterModel(QAbstractTableModel):
    """
    Data model that edits a simple parameter (currently only scalars) in place.
    """

    def __init__(self, data):
        QAbstractTableModel.__init__(self)
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
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, rowcol, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return "Value"
        return None


class ParameterModel(QAbstractTableModel):
    """
    Data model that edits index tuple-value pairs in place and augments the table
    with lookup text for identification.
    """

    def __init__(self, data, index_sets, lookup, spec):
        QAbstractTableModel.__init__(self)
        self.df = mqu.ref_id_to_text(index_sets, data["Index"].to_list(), spec, lookup)

        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1] + self.df.shape[1]

    def data(self, index, role=Qt.EditRole):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole:
                if index.column() < len(self._data.columns):
                    return str(self._data.iloc[index.row(), index.column()])
                elif index.column() < len(self._data.columns) + len(self.df.columns):
                    return str(self.df.iloc[index.row(), index.column() - len(self._data.columns)])
        return None

    def setData(self, index, value, role):
        if index.isValid() and role == Qt.EditRole and index.column() < len(self._data.columns):
            self._data.iloc[index.row(), index.column()] = float(value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        if index.column() < len(self._data.columns) and self._data.columns[index.column()] == 'Value':
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, rowcol, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if len(self._data.columns) > 0 and rowcol < len(self._data.columns):
                return self._data.columns[rowcol]
            elif rowcol < len(self._data.columns) + len(self.df.columns):
                return self.df.columns[rowcol - len(self._data.columns)]

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

