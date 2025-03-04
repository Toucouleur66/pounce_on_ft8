from PyQt6.QtCore import QObject, pyqtSignal

class ProcessorWorker(QObject):
    processing_done = pyqtSignal()

    def __init__(self, process_function):
        super().__init__()
        self.process_function = process_function
        self._running = True

    def run(self):
        while self._running:
            self.process_function()
        try:
            self.processing_done.emit()
        except RuntimeError:
            pass

    def stop(self):
        self._running = False