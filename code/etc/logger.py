import logging
import os

from os import mkdir
from colorama import Fore
from datetime import datetime, UTC


from typing import Optional




class Formatter(logging.Formatter):
    COLORS = [
        (logging.DEBUG, Fore.LIGHTBLACK_EX),
        (logging.INFO, Fore.LIGHTCYAN_EX),
        (logging.WARNING, Fore.YELLOW),
        (logging.WARN, Fore.YELLOW),
        (logging.ERROR, Fore.RED),
        (logging.CRITICAL, Fore.LIGHTWHITE_EX)
    ]

    FORMATS = {
        level: logging.Formatter(
            f'{Fore.LIGHTBLACK_EX}%(asctime)s{Fore.RESET} [ {color}%(levelname)s{Fore.RESET} ] {Fore.MAGENTA}%(name)s: {color}%(message)s{Fore.RESET}',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, color in COLORS
    }

    def format(self, record: logging.LogRecord):
        formatter = self.FORMATS.get(record.levelno)

        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        record.levelname = record.levelname.center(8)
        
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'{Fore.RED}{text}{Fore.RESET}'

        output = formatter.format(record)

        record.exc_text = None
        return output


 
class ClassicFormatter(logging.Formatter):
    LEVELS = [
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.WARN,
        logging.ERROR,
        logging.CRITICAL
    ]

    FORMATS = {
        level: logging.Formatter(
            f'%(asctime)s [ %(levelname)s ] %(name)s: %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level in LEVELS
    }

    def format(self, record: logging.LogRecord):
        formatter = self.FORMATS.get(record.levelno)

        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        record.levelname = record.levelname.center(8)
        
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'{Fore.RED}{text}{Fore.RESET}'

        output = formatter.format(record)

        record.exc_text = None
        return output
    


def create_logger(name: str, level: Optional[int] = None):
    filename = 'logs/app_{}{}.log'
    filename = filename.format(name, datetime.now(UTC).strftime(r'%y-%m-%d_%H-%M-%S'))
    if not os.path.exists('logs'):
        mkdir('logs')

    logger = logging.getLogger()
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(filename=filename)
    file_handler2 = logging.FileHandler(filename=f'logs/app_{name}.log')

    _formatter = ClassicFormatter()
    formatter = Formatter()

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(_formatter)
    file_handler2.setFormatter(_formatter)

    file_handler.setLevel(logging.DEBUG)
    file_handler2.setLevel(logging.DEBUG)

    logger.setLevel(level or logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(file_handler2)
    logger.addHandler(console_handler)
    return console_handler
    