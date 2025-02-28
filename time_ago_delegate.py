from PyQt6 import QtWidgets, QtCore

from utils import compute_time_ago

class TimeAgoDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        row_data = index.data(QtCore.Qt.ItemDataRole.UserRole)

        if isinstance(row_data, dict) and 'row_datetime' in row_data:
            option.text = compute_time_ago(row_data["row_datetime"])
            option.displayAlignment = QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
