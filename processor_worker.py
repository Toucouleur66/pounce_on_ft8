from PyQt6.QtCore import QObject, pyqtSignal

class ProcessorWorker(QObject):
    # Signal émis quand le traitement est terminé
    processing_done = pyqtSignal()

    def __init__(self, process_function):
        super().__init__()
        self.process_function = process_function
        self._running = True

    def run(self):
        # Exécute la fonction de traitement en continu
        while self._running:
            self.process_function()
        self.processing_done.emit()

    def stop(self):
        self._running = False