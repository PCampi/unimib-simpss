"""Custom logging facilities."""

import logging


def get_logger(name: str):
    """Get a logger to use in this class."""
    logger = logging.getLogger(name=name)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger
