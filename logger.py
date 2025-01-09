# logger.py

import logging
import sys
from colorama import init, Back, Fore, Style

# Init colorama for Windows
init()

# LOG_FORMAT = "%(asctime)s @%(name)s [%(levelname)s] | %(message)s"
LOG_FORMAT = "[%(asctime)s @%(name)s] %(levelname)s --:\n\t%(message)s"

class ColoredFormatter(logging.Formatter):
    COLOR_MAP = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Back.RED + Fore.WHITE,
    }

    def format(self, record):
        # Use first name only for log level
        record.level_short = record.levelname[0]
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

    date_format = "%y%m%d_%H%M%S"  # YYMMDD_HHMMSS        

    console_handler = logging.StreamHandler(sys.stderr)
    console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

def add_file_handler(filename):
    root_logger = logging.getLogger()
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt="%y%m%d_%H%M%S")    
    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    root_logger.info(f"FileHandler set:{filename}")
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
    gui_logger.setLevel(logging.DEBUG)
    gui_logger.propagate = False 
    return gui_logger
