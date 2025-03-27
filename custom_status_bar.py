from PyQt6 import QtWidgets, QtCore

class CustomStatusBar(QtWidgets.QStatusBar):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()