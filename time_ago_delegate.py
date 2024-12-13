from PyQt6 import QtWidgets, QtCore

from datetime import datetime, timezone

from constants import (
    CUSTOM_FONT_SMALL,
)

class TimeAgoDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        user_data = index.data(QtCore.Qt.ItemDataRole.UserRole)

        if isinstance(user_data, dict) and 'datetime' in user_data:
            value = user_data['datetime']
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
            else:
                option.text = f"{int(seconds // 86_400)}d"

            option.displayAlignment = QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
