# logger.py

import logging
import sys
from colorama import init, Back, Fore, Style
from termcolor import colored

init()

LOG_FORMAT = "%(asctime)s | %(message)s"

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
    

class Logger(object):
    def __init__(self, logger):
        self.logger = logger
        self.file_handler = None

    def add_file_handler(self, filename):
        if not self.file_handler:
            file_handler = logging.FileHandler(filename)
            file_formatter = logging.Formatter(LOG_FORMAT)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            self.file_handler = file_handler
            self.logger.info(f"FileHandler set for {filename}")

    def remove_file_handler(self):
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None
            self.logger.info("FileHandler removed")

    def __getattr__(self, attr_name):
        if attr_name == 'warn':
            attr_name = 'warning'
        if attr_name not in ['debug', 'info', 'warning', 'error', 'critical']:
            return getattr(self.logger, attr_name)
        log_level = getattr(logging, attr_name.upper())

        def wrapped_attr(msg, *args, **kwargs):
            if not self.logger.isEnabledFor(log_level):
                return
            # Do not use any ANSI code here
            return self.logger._log(log_level, msg, args, **kwargs)
        return wrapped_attr

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stderr)
    console_formatter = ColoredFormatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG, stream=sys.stderr)
LOGGER = Logger(get_logger(__name__))
