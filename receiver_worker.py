from PyQt6.QtCore import QObject, pyqtSignal, QThread

class ReceiverWorker(QObject):
    packet_received = pyqtSignal(object, object)

    def __init__(self, receive_function):
        super().__init__()
        self.receive_function = receive_function
        self._running = True

    def run(self):
        while self._running:
            result = self.receive_function()
            if result is not None:
                packet, addr_port = result 
                self.packet_received.emit(packet, addr_port)

    def stop(self):
        self._running = False