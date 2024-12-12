from PyQt6 import QtWidgets, QtGui, QtCore

class SearchFilterInput(QtWidgets.QWidget):
    cleared = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()

    def create_search_field(self, placeholder_text):
        line_edit = SearchLineEdit(placeholder_text)
        line_edit.setFixedWidth(150)
        line_edit.setFixedHeight(20)
        line_edit.setStyleSheet("""
            QLineEdit {
                border-radius: 4px;
                font-size: 11px;
                padding-right: 20px; 
            }
        """)
        
        clear_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-clear"), "", line_edit)
        line_edit.addAction(clear_action, QtWidgets.QLineEdit.ActionPosition.TrailingPosition)
        clear_action.setVisible(False)  
        
        line_edit.textChanged.connect(lambda text: clear_action.setVisible(bool(text.strip())))
        clear_action.triggered.connect(lambda: self.clear_line_edit(line_edit, clear_action))
        line_edit.clearRequested.connect(lambda: self.clear_line_edit(line_edit, clear_action))  

        
        return line_edit

    def clear_line_edit(self, line_edit, clear_action):
        line_edit.clear()
        clear_action.setVisible(False)
        self.cleared.emit()

class SearchLineEdit(QtWidgets.QLineEdit):
    clearRequested = QtCore.pyqtSignal()

    def __init__(self, placeholder_text):
        super().__init__()
        self.setPlaceholderText(placeholder_text)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.clearRequested.emit()
        else:
            super().keyPressEvent(event)