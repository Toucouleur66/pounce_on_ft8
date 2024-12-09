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

                hovered = widget.rect().contains(widget.mapFromGlobal(QtGui.QCursor.pos()))
                pressed = bool(QtWidgets.QApplication.mouseButtons() & QtCore.Qt.MouseButton.LeftButton)

                if  hovered and not pressed: 
                    bg_color = widget.property("hover_bg_color") or "#FFFFFF"
                    fg_color = widget.property("fg_color") or "#000000"
                    bd_color = widget.property("bd_color") or "#FFFFFF"
                elif pressed:
                    bg_color = widget.property("hover_bg_color") or "#FFFFFF"
                    fg_color = widget.property("fg_color") or "#000000"
                    bd_color = widget.property("bd_color") or "#B6B6B6"

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

    def setVisibleState(self, visible):
        if visible:
            self.setStyleSheet("")  
            self.setEnabled(True) 
        else:
            self.setStyleSheet("background-color: transparent; color: transparent; border: none;")
            self.setEnabled(False)        
        
    def setHoverColors(self, bg_color, bd_color=None):
        self.setProperty("hover_bg_color", bg_color)
        if bd_color:
            self.setProperty("hover_bd_color", bd_color)
        self.style().polish(self)

    def hitButton(self, pos: QtCore.QPoint) -> bool:
        rect = self.rect()
        radius = 8  

        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), radius, radius)

        region = QtGui.QRegion(path.toFillPolygon().toPolygon())

        return region.contains(pos)