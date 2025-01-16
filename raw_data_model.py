# raw_data_model.py

from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from constants import (
    FG_COLOR_FOCUS_MY_CALL,
    BG_COLOR_FOCUS_MY_CALL,
    BG_COLOR_BLACK_ON_YELLOW,
    FG_COLOR_BLACK_ON_YELLOW,
    BG_COLOR_WHITE_ON_BLUE,
    FG_COLOR_WHITE_ON_BLUE,
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    BG_COLOR_BLACK_ON_CYAN,
    FG_COLOR_BLACK_ON_CYAN,
    CUSTOM_FONT,
    CUSTOM_FONT_SMALL
)
class RawDataModel(QtCore.QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["Date", "Band", "SNR", "Δ Time", "Δ Freq", "Message", "Country", "CQ Zone", "Continent", "WKB4 Year"]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)
    
    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return self._headers[section]
            else:
                return str(section + 1)
        return None

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        column = index.column()
        raw_data = self._data[row]

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return raw_data["date_str"]
            elif column == 1:
                return raw_data["band"]
            elif column == 2:
                return f"{raw_data['snr']:+3d} dB"
            elif column == 3:
                return f"{raw_data['delta_time']:+5.1f}s"
            elif column == 4:
                return f"{raw_data['delta_freq']:+6d}Hz"
            elif column == 5:
                return f" {raw_data['message']}"
            elif column == 6:
                return raw_data['entity']
            elif column == 7:
                return str(raw_data['cq_zone'])
            elif column == 8:
                return raw_data['continent']
            elif column == 9:
                return raw_data['wkb4_year'] or ""
        elif role == Qt.ItemDataRole.BackgroundRole:
            row_color = raw_data.get('row_color')
            if row_color:
                color = self.get_color(row_color)
                if color:
                    return color
        elif role == Qt.ItemDataRole.ForegroundRole:
            row_color = raw_data.get('row_color')
            if row_color:
                color = self.get_foreground_color(row_color)
                if color:
                    return color
        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if column in [1, 2, 3, 4]:
                return QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            elif column in [7, 8, 9]:
                return QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
            else:
                return QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            if column == 5 or column == 6:
                return CUSTOM_FONT
            else:
                return CUSTOM_FONT_SMALL
        elif role == QtCore.Qt.ItemDataRole.UserRole:
            return raw_data            

        return None

    def add_raw_data(self, raw_data):
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(raw_data)
        self.endInsertRows()

    def remove_raw_data_at(self, index):
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        del self._data[index]
        self.endRemoveRows()        

    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

    def findRowByUid(self, uid):
        for i, row_data in enumerate(self._data):
            if row_data.get('uid') == uid:
                return i
        return -1

    def get_color(self, row_color):
        color_map = {
                    'bright_for_my_call'    : BG_COLOR_FOCUS_MY_CALL,
                    'black_on_yellow'       : BG_COLOR_BLACK_ON_YELLOW,
                    'black_on_purple'       : BG_COLOR_BLACK_ON_PURPLE,
                    'white_on_blue'         : BG_COLOR_WHITE_ON_BLUE,
                    'black_on_cyan'         : BG_COLOR_BLACK_ON_CYAN,
                }
        return QColor(color_map.get(row_color, "#FFFFFF"))

    def get_foreground_color(self, row_color):
        fg_color_map = {
                    'bright_for_my_call'    : FG_COLOR_FOCUS_MY_CALL,
                    'black_on_yellow'       : FG_COLOR_BLACK_ON_YELLOW,
                    'black_on_purple'       : FG_COLOR_BLACK_ON_PURPLE,
                    'white_on_blue'         : FG_COLOR_WHITE_ON_BLUE,
                    'black_on_cyan'         : FG_COLOR_BLACK_ON_CYAN,
                }
        return QColor(fg_color_map.get(row_color, "#000000"))
    