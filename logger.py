# logger.py

import logging
import sys
from colorama import init, Back, Fore, Style

# Init colorama for Windows
init()

LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

class ColoredFormatter(logging.Formatter):
    COLOR_MAP = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Back.RED + Fore.WHITE,
    }

    def format(self, record):
        color = self.COLOR_MAP.get(record.levelname, "")
        message = super().format(record)
        if color:
            message = f"{color}{message}{Style.RESET_ALL}"
        return message

def configure_root_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stderr)
    console_formatter = ColoredFormatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

def add_file_handler(filename):
    root_logger = logging.getLogger()
    file_handler = logging.FileHandler(filename)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    root_logger.info(f"FileHandler set for {filename}")
    return file_handler

def remove_file_handler(file_handler):
    root_logger = logging.getLogger()
    root_logger.removeHandler(file_handler)
    file_handler.close()
    root_logger.info("FileHandler removed")

configure_root_logger()

def get_logger(name):
    return logging.getLogger(name)

LOGGER = get_logger(__name__)
LOGGER.setLevel(logging.WARNING)
LOGGER.propagate = False  

def get_gui_logger():
    gui_logger = get_logger('gui')
    gui_logger.setLevel(logging.INFO)
    gui_logger.propagate = False 
    return gui_logger
