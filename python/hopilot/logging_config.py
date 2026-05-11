"""
Centralized logging configuration for HoPilot application.

This module provides a unified logging setup with colored console output
and file logging capabilities.
"""

import logging
import os
import sys
import time
from functools import wraps
from logging.handlers import RotatingFileHandler

import colorama
from colorama import Fore, Back, Style


def timing_decorator(func):
    """
    Decorator that logs the execution time of a function.

    Args:
        func: Function to time

    Returns:
        Wrapped function that logs execution time
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time

        # Get logger for the function's module
        logger = logging.getLogger(func.__module__)
        logger.debug(f"{func.__name__} executed in {execution_time:.4f} seconds")

        return result
    return wrapper


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels for console output."""

    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }

    def format(self, record):
        # Save the original levelname
        original_levelname = record.levelname

        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{Style.RESET_ALL}"

        # Format the message
        result = super().format(record)

        # Restore original levelname for other handlers
        record.levelname = original_levelname

        return result


def setup_logging(log_level=logging.INFO, log_dir=None):
    """
    Set up centralized logging configuration with colored console and rotating file handlers.

    Args:
        log_level: Logging level (default: INFO)
        log_dir: Directory for log files (default: 'logs' relative to this module)

    Returns:
        logging.Logger: Configured root logger
    """
    # Initialize colorama for cross-platform colored output
    colorama.init()

    # Determine log directory
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(__file__), "logs")

    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    console_formatter = ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Rotating file handler (128MB max size, keep 5 backup files)
    log_file = os.path.join(log_dir, "hopilot.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=128 * 1024 * 1024, backupCount=5  # 128MB
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Log the setup
    logger.info("Logging initialized")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")

    return logger


def get_logger(name):
    """
    Get a logger with the specified name.

    This ensures all loggers use the centralized configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


# Initialize logging when this module is imported
_root_logger = setup_logging()