from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QBrush, QPen
from PyQt6.QtCore import Qt

class ColorRowDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()

        text = index.data(Qt.ItemDataRole.DisplayRole)

        custom_font = index.data(Qt.ItemDataRole.FontRole)
        if custom_font:
            painter.setFont(custom_font)

        bg_color = index.data(Qt.ItemDataRole.BackgroundRole)
        if bg_color:
            painter.setBrush(QBrush(bg_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(option.rect)

        fg_color = index.data(Qt.ItemDataRole.ForegroundRole)

        if fg_color:
            painter.setPen(QPen(fg_color))
        else:
            text_color = option.palette.color(option.palette.ColorRole.Text)
            painter.setPen(QPen(text_color))

        text_rect = option.rect.adjusted(5, 0, -5, 0)
        alignment = index.data(Qt.ItemDataRole.TextAlignmentRole) or (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if text is None:
            text = ""

        painter.drawText(text_rect, alignment, str(text))

        # Draw strikethrough across entire message column width for excluded items
        raw_data = index.data(Qt.ItemDataRole.UserRole)
        if raw_data and raw_data.get('excluded') and index.column() == 5:  # Column 5 is the message column
            painter.setPen(QPen(fg_color if fg_color else text_color, 1))
            y_center = option.rect.center().y()
            painter.drawLine(option.rect.left(), y_center, option.rect.right(), y_center)

        painter.restore()