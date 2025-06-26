# priority_table.py

from PyQt6 import QtGui
from PyQt6.QtWidgets import QTableWidgetItem, QTableWidget
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from constants import (
    # Colors
    BG_COLOR_BLACK_ON_PURPLE
)

class PriorityTableWidget(QTableWidget):
    rowsMoved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        self.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.toggle_blink)
        self.blink_count = 0
        self.blink_row = -1
        self.original_bg_colors = []
        
    def dropEvent(self, event):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)
            rows = sorted(set(item.row() for item in self.selectedItems()))
            
            rows_data = []
            for row_index in rows:
                row_data = []
                for column_index in range(self.columnCount()):
                    item = self.item(row_index, column_index)
                    if item:
                        item_data = {
                            'text': item.text(),
                            'alignment': item.textAlignment(),
                            'flags': item.flags(),
                            'font': item.font()
                        }
                        row_data.append(item_data)
                    else:
                        row_data.append(None)
                rows_data.append(row_data)

            for row_index in reversed(rows):
                self.removeRow(row_index)
                if row_index < drop_row:
                    drop_row -= 1

            for row_index, row_data in enumerate(rows_data):
                row_index += drop_row
                self.insertRow(row_index)
                # Set fixed row height
                self.setRowHeight(row_index, 22)
                for column_index, item_data in enumerate(row_data):
                    if item_data:
                        new_item = QTableWidgetItem(item_data['text'])
                        new_item.setTextAlignment(item_data['alignment'])
                        new_item.setFlags(item_data['flags'])
                        new_item.setFont(item_data['font'])
                        self.setItem(row_index, column_index, new_item)
            event.accept()
            self.rowsMoved.emit()
            
            # Start blinking the moved row
            if rows_data:
                self.start_blink(drop_row)
        super().dropEvent(event)

    def drop_on(self, event):
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            return self.rowCount()
        return index.row() + 1 if self.is_below(event, index) else index.row()

    def is_below(self, event, model_index):
        rect = self.visualRect(model_index)
        margin = 2
        if event.position().y() - rect.top() < margin:
            return False
        elif rect.bottom() - event.position().y() < margin:
            return True
        return event.position().y() >= rect.center().y()
    
    def start_blink(self, row):
        self.stop_blink() 
        self.blink_row = row
        self.blink_count = 0
        
        self.original_bg_colors = []
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                self.original_bg_colors.append(item.background())
            else:
                self.original_bg_colors.append(None)
                
        self.blink_timer.start(125)
    
    def toggle_blink(self):
        if self.blink_row >= 0 and self.blink_row < self.rowCount():
            for col in range(self.columnCount()):
                item = self.item(self.blink_row, col)
                if item:
                    if self.blink_count % 2 == 0:
                        item.setBackground(QtGui.QBrush(QtGui.QColor(BG_COLOR_BLACK_ON_PURPLE)))
                    else:
                        if col < len(self.original_bg_colors) and self.original_bg_colors[col]:
                            item.setBackground(self.original_bg_colors[col])
                        else:
                            item.setBackground(QtGui.QBrush())
            
            self.blink_count += 1
            if self.blink_count >= 4:  
                self.stop_blink()
    
    def stop_blink(self):
        self.blink_timer.stop()
        if self.blink_row >= 0 and self.blink_row < self.rowCount():
            for col in range(self.columnCount()):
                item = self.item(self.blink_row, col)
                if item:
                    if col < len(self.original_bg_colors) and self.original_bg_colors[col]:
                        item.setBackground(self.original_bg_colors[col])
                    else:
                        item.setBackground(QtGui.QBrush()) 
        self.blink_row = -1
        self.original_bg_colors = []
