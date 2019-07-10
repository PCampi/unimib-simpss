"""utilities."""

import logging
from typing import Dict

import pandas as pd


def get_logger(name='link-mqtt-kafka') -> logging.Logger:
    logger = logging.getLogger(name=name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


def read_sensor_group_mapping(file_path) -> Dict[int, str]:
    """Read the mapping from sensor_id to group_id and return
    a dict.
    """
    table = pd.read_csv(file_path)

    # check that all strings and ids have values
    if table.isna().any().any():
        raise ValueError("sensor file contains missing values")

    # check that there are no repeated sensor_id
    if table.duplicated(subset=['sensor_id'], keep=False).any():
        raise ValueError("column 'sensor_id' contains duplicates, not allowed")

    result = {
        int(row['sensor_id']): str.strip(row['group_id'])
        for _, row in table.iterrows()
    }

    return result
