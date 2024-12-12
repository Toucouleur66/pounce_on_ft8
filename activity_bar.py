# activity_bar.py

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QEasingCurve


from constants import (
    ACTIVITY_BAR_MAX_VALUE
    )

class ActivityBar(QtWidgets.QWidget):
    def __init__(self, parent=None, max_value=ACTIVITY_BAR_MAX_VALUE):
        super(ActivityBar, self).__init__(parent)
        self.max_value = max_value
        self.current_value = 0
        self.render_value = 0  
        self.is_overflow = False  # Indicateur pour valeur dépassant le maximum
        self.setMinimumSize(50, 200)
        self.animation = QtCore.QPropertyAnimation(self, b"displayedValue")
        self.animation.setDuration(1_000)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)  

    @QtCore.pyqtProperty(float)
    def displayedValue(self):
        return self.render_value

    @displayedValue.setter
    def displayedValue(self, value):
        self.render_value = value
        self.update()

    def setValue(self, value):
        self.is_overflow = value > self.max_value 
        self.animation.stop()
        self.animation.setStartValue(self.render_value)
        self.animation.setEndValue(min(value, self.max_value))
        self.animation.start()    

    def setColors(self, background_color, text_color, border_color):
        self.background_color = QtGui.QColor(background_color)
        self.text_color = QtGui.QColor(text_color)
        self.border_color = QtGui.QColor(border_color)
        self.update()        

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        rect = self.rect()

        painter.fillRect(rect, self.background_color)
        painter.setPen(QtGui.QPen(self.border_color, 2))
        painter.drawRect(rect.adjusted(0, 0, 0, 0))

        content_rect = rect.adjusted(1, 2, -1, 0)
        fill_height = content_rect.height() * (self.render_value / self.max_value)
        y = content_rect.bottom() - fill_height
        filled_rect = QtCore.QRectF(content_rect.left(), y, content_rect.width(), fill_height)

        gradient = QtGui.QLinearGradient(
            QtCore.QPointF(content_rect.topLeft()),
            QtCore.QPointF(content_rect.bottomLeft())
        )
        gradient.setColorAt(0, QtGui.QColor("#EC9A22"))  
        gradient.setColorAt(1, QtGui.QColor("#03FE00"))  

        painter.setBrush(gradient)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawRect(filled_rect)

        painter.setPen(QtGui.QPen(self.text_color))
        if self.is_overflow:
            text = f"{int(self.max_value)}+"
        else:
            text = str(int(self.render_value))
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)
