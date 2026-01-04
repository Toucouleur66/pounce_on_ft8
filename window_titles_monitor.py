import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import QTimer

from custom_button import CustomButton
from window_controller import WindowController

class WindowTitlesMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Window Titles Monitor")
        self.setGeometry(100, 100, 600, 500)

        # Create window controller
        self.controller = WindowController()

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Title label
        title_label = QLabel("Open Windows")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)

        # Count label
        self.count_label = QLabel("Windows found: 0")
        self.count_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.count_label)

        # List widget to display window titles
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("padding: 5px;")
        layout.addWidget(self.list_widget)

        # Button layout
        button_layout = QHBoxLayout()

        # Refresh button
        refresh_button = QPushButton("Refresh Now")
        refresh_button.clicked.connect(self.update_window_list)
        button_layout.addWidget(refresh_button)

        # Toggle auto-refresh button
        self.auto_refresh_button = QPushButton("Pause Auto-Refresh")
        self.auto_refresh_button.clicked.connect(self.toggle_auto_refresh)
        button_layout.addWidget(self.auto_refresh_button)

        layout.addLayout(button_layout)

        # Timer for auto-refresh every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_window_list)
        self.timer.start(1000)  # Update every 1000ms (1 second)
        self.auto_refresh_enabled = True

        # Initial update
        self.update_window_list()

    def update_window_list(self):
        # Get window titles using WindowController
        windows_list = self.controller.get_windows_list()

        # Extract display strings
        windows = [window['display'] for window in windows_list]

        # Clear and update list
        self.list_widget.clear()

        # Sort windows alphabetically
        windows.sort()

        # Add to list widget
        for window in windows:
            self.list_widget.addItem(window)

        # Update count
        self.count_label.setText(f"Windows found: {len(windows)}")

    def toggle_auto_refresh(self):
        if self.auto_refresh_enabled:
            self.timer.stop()
            self.auto_refresh_button.setText("Resume Auto-Refresh")
            self.auto_refresh_enabled = False
        else:
            self.timer.start(1000)
            self.auto_refresh_button.setText("Pause Auto-Refresh")
            self.auto_refresh_enabled = True


def main():
    app = QApplication(sys.argv)
    window = WindowTitlesMonitor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
