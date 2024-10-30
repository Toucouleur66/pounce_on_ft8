# gui_handler.py

import logging

class GUIHandler(logging.Handler):
    def __init__(self, message_callback):
        super().__init__()
        self.message_callback = message_callback

    def emit(self, record):
        msg = self.format(record)
        if self.message_callback:
            self.message_callback(msg)