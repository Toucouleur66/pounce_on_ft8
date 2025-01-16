from PyQt6 import QtWidgets, QtCore

from datetime import datetime, timezone

class TimeAgoDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        row_data = index.data(QtCore.Qt.ItemDataRole.UserRole)

        if isinstance(row_data, dict) and 'row_datetime' in row_data:
            value = row_data['row_datetime']
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - value
            seconds = delta.total_seconds()
            if seconds < 60:
                option.text = f"{int(seconds)}s"
            elif seconds < 3_600:
                option.text = f"{int(seconds // 60)}m"
            elif seconds < 86_400:
                option.text = f"{int(seconds // 3_600)}h"
            elif seconds <= 1_209_600:  # 2 weeks in seconds
                option.text = f"{int(seconds // 86_400)}d"
            else:
                weeks = seconds // (86_400 * 7)
                option.text = f"{int(weeks)}w"

            option.displayAlignment = QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
