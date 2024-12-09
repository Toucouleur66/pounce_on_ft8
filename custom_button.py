from PyQt6 import QtWidgets, QtGui, QtCore

class CustomButtonStyle(QtWidgets.QProxyStyle):
    def drawControl(self, element, option, painter, widget=None):
        if element == QtWidgets.QStyle.ControlElement.CE_PushButton and isinstance(option, QtWidgets.QStyleOptionButton):
            if widget and isinstance(widget, QtWidgets.QPushButton):
                painter.save()
                painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

                rect = option.rect.adjusted(1, 1, -1, -1)
                bg_color = widget.property("bg_color") or "#E0E0E0"
                fg_color = widget.property("fg_color") or "#000000"
                bd_color = widget.property("bd_color") or "#E0E0E0"

                hovered = bool(option.state & QtWidgets.QStyle.StateFlag.State_MouseOver)
                pressed = bool(option.state & QtWidgets.QStyle.StateFlag.State_Sunken)

                if  hovered and not pressed: 
                    bg_color = widget.property("hover_bg_color") or bg_color
                    fg_color = widget.property("fg_color") or "#000000"
                    bd_color = widget.property("bd_color") or "#BBBBBB"

                painter.setBrush(QtGui.QBrush(QtGui.QColor(bg_color)))
                painter.setPen(QtGui.QPen(QtGui.QColor(bd_color), 2))
                painter.drawRoundedRect(rect, 8, 8)  

                if bd_color:
                    pen = QtGui.QPen(QtGui.QColor(bd_color), 0.5)
                    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)  
                    painter.setPen(pen)
                    painter.drawRoundedRect(rect, 8, 8)

                painter.setPen(QtGui.QColor(fg_color))
                painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, option.text)

                painter.restore()
                return

        super().drawControl(element, option, painter, widget)

class CustomButton(QtWidgets.QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        style = CustomButtonStyle(QtWidgets.QApplication.style())
        QtWidgets.QApplication.setStyle(style)
        
    def setHoverColors(self, bg_color, bd_color=None):
        self.setProperty("hover_bg_color", bg_color)
        if bd_color:
            self.setProperty("hover_bd_color", bd_color)
        self.style().polish(self)