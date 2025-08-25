# raw_data_model.py

from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from pympler import asizeof

from utils import compute_time_ago

from constants import (
    FG_COLOR_FOCUS_MY_CALL,
    BG_COLOR_FOCUS_MY_CALL,
    BG_COLOR_BLACK_ON_YELLOW,
    FG_COLOR_BLACK_ON_YELLOW,
    BG_COLOR_BLACK_ON_SAUMON,
    FG_COLOR_BLACK_ON_SAUMON,
    BG_COLOR_WHITE_ON_BLUE,
    FG_COLOR_WHITE_ON_BLUE,
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    BG_COLOR_BLACK_ON_CYAN,
    FG_COLOR_BLACK_ON_CYAN,
    CUSTOM_FONT,
    CUSTOM_FONT_SMALL,
    DATE_COLUMN_AGE
)
class RawDataModel(QtCore.QAbstractTableModel):
    def __init__(self, data=None, max_size_bytes=50**7, max_num_rows=20_000):
        super().__init__()
        self._data = data or []
        self._headers = [
            "Time",
            "Band",
            "Report",
            "DT",
            "Freq",
            "Message",
            "", # LoTW
            "Country",
            "CQ Zone",
            "Continent",
            "WKB4"
        ]
        self.datetime_column_setting    = None
        # Useless we might need to remove max_size_bytes
        self._max_size_bytes            = max_size_bytes
        self._max_num_rows              = max_num_rows
        self._current_size_bytes        = None

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def setTimeMode(self, value: bool):
        self.datetime_column_setting = value

        top_left    = self.index(0, 0)
        bottom_right= self.index(self.rowCount()-1, 0)
        self.dataChanged.emit(top_left, bottom_right, [QtCore.Qt.ItemDataRole.DisplayRole])

        self.headerDataChanged.emit(QtCore.Qt.Orientation.Horizontal, 0, 0)

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):               
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return self._headers[section]
            else:
                return str(section + 1)                
        
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                if section == 0 and self.datetime_column_setting == DATE_COLUMN_AGE:
                    return QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
                elif section in [1, 2, 3, 4]:
                    return QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
                elif section in [6, 8, 9, 10]:  # Adjusted for new LoTW column (6) and shifted other columns
                    return QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
                else:
                    return QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        
        return None

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        column = index.column()
        raw_data = self._data[row]

        if raw_data.get("is_message_row", False):
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                return raw_data["message"]
            elif role == QtCore.Qt.ItemDataRole.BackgroundRole:
                return QColor(raw_data["bg_color"])
            elif role == QtCore.Qt.ItemDataRole.ForegroundRole:
                return QColor(raw_data["fg_color"])
            elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
                return QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter

            return None

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == 0:                
                if self.datetime_column_setting == DATE_COLUMN_AGE and "row_datetime" in raw_data:
                    return compute_time_ago(raw_data["row_datetime"])
                else:
                    return raw_data['date_str']
            elif column == 1:
                return raw_data['band']
            elif column == 2:
                return f"{raw_data['snr']:+3d} dB"
            elif column == 3:
                return f"{raw_data['delta_time']:+5.1f}s"
            elif column == 4:
                return f"{raw_data['delta_freq']:+6d}Hz"
            elif column == 5:
                return f" {raw_data['message']}"
            elif column == 6:
                # LoTW indicator column
                lotw = raw_data.get('lotw')
                return "•" if lotw else ""
            elif column == 7:
                # Country column (moved from column 6)
                return raw_data['entity']
            elif column == 8:
                return str(raw_data['cq_zone'])
            elif column == 9:  
                return raw_data['continent']
            elif column == 10:
                return raw_data['wkb4_year'] or ""
        elif role == Qt.ItemDataRole.BackgroundRole:
            # Check for individual cell coloring based on message_type
            message_type = raw_data.get('message_type')
            if message_type == 'snr_below_minimum' and column == 2:  # SNR column
                return QColor(FG_COLOR_FOCUS_MY_CALL) 
            elif message_type == 'dt_above_normal' and column == 3:  # DT column
                return QColor(FG_COLOR_FOCUS_MY_CALL) 
            # Fall back to row-level coloring
            row_color = raw_data.get('row_color')
            if row_color:
                color = self.get_color(row_color)
                if color:
                    return color
        elif role == Qt.ItemDataRole.ForegroundRole:
            # Check for individual cell coloring based on message_type
            message_type = raw_data.get('message_type')
            if message_type == 'snr_below_minimum' and column == 2:  # SNR column
                return QColor(BG_COLOR_FOCUS_MY_CALL)
            elif message_type == 'dt_above_normal' and column == 3:  # DT column
                return QColor(BG_COLOR_FOCUS_MY_CALL) 
            # Fall back to row-level coloring
            row_color = raw_data.get('row_color')
            if row_color:
                color = self.get_foreground_color(row_color)
                if color:
                    return color
        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if column == 0:
                if self.datetime_column_setting == DATE_COLUMN_AGE:
                    return QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
                else:
                    return QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
            elif column in [1, 2, 3, 4]:
                return QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            elif column in [6, 8, 9, 10]:  # LoTW column (6) and shifted columns
                return QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
            else:
                return QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            if column == 5 or column == 7:  # Message column (5) and Country column (7)
                return CUSTOM_FONT
            else:
                return CUSTOM_FONT_SMALL
        elif role == QtCore.Qt.ItemDataRole.UserRole:
            return raw_data            

        return None
    
    def setHeaderData(self, section, orientation, value, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            self._headers[section] = value
            self.headerDataChanged.emit(orientation, section, section)
            return True
        return super().setHeaderData(section, orientation, value, role)    

    def add_message_row(self, message, fg_color, bg_color):    
        raw_data = {
            'is_message_row': True,
            'message'       : message,
            'fg_color'      : fg_color,
            'bg_color'      : bg_color
        }
        self.add_raw_data(raw_data)  

    def add_raw_data(self, raw_data):
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(raw_data)
        self.endInsertRows()

    def enforce_size_limit(self):        
        if len(self._data) > self._max_num_rows:
            self._current_size_bytes = asizeof.asizeof(self._data)        
            rows_to_remove = int(len(self._data) * 0.01)        
        
            self.beginRemoveRows(QtCore.QModelIndex(), 0, rows_to_remove - 1)
            del self._data[0:rows_to_remove]
            self.endRemoveRows()

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
            if row_data.get('message_uid') == uid:
                return i
        return -1

    def get_color(self, row_color):
        # row_color is now the hex color string directly from constants
        return QColor(row_color)

    def get_foreground_color(self, row_color):
        # Map background colors to their corresponding foreground colors
        if row_color == BG_COLOR_FOCUS_MY_CALL:
            return QColor(FG_COLOR_FOCUS_MY_CALL)
        elif row_color == BG_COLOR_BLACK_ON_YELLOW:
            return QColor(FG_COLOR_BLACK_ON_YELLOW)
        elif row_color == BG_COLOR_BLACK_ON_SAUMON:
            return QColor(FG_COLOR_BLACK_ON_SAUMON)
        elif row_color == BG_COLOR_BLACK_ON_PURPLE:
            return QColor(FG_COLOR_BLACK_ON_PURPLE)
        elif row_color == BG_COLOR_WHITE_ON_BLUE:
            return QColor(FG_COLOR_WHITE_ON_BLUE)
        elif row_color == BG_COLOR_BLACK_ON_CYAN:
            return QColor(FG_COLOR_BLACK_ON_CYAN)
        else:
            return QColor(FG_COLOR_BLACK_ON_CYAN)  
    