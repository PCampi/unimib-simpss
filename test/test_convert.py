"""Test for the conversion module."""

import pytest

from simpss_persistence.data_mapping import convert


def test_convert_ok():
    """Test the convert function."""
    original = {
        'time_received': 123,
        'sensor_group': 2,
        'id': 3,
        'P': 432,
        'T': 918,
        'Ix': -235,
        'M': 56,
    }

    target = {
        'time_received': 123,
        'sensor_group': 2,
        'sensor_id': 3,
        'pressure': 432,
        'temperature': 918,
        'ix': -235,
        'mask': 56,
    }

    mapping = {
        'time_received': 'time_received',
        'sensor_group': 'sensor_group',
        'id': 'sensor_id',
        'P': 'pressure',
        'T': 'temperature',
        'Ix': 'ix',
        'M': 'mask',
    }

    converted = convert(original, mapping)
    assert converted == target


def test_convert_raises():
    """Test that convert raises if a key is missing in the mapping."""
    original = {
        'time_received': 123,
        'sensor_group': 2,
        'id': 3,
        'P': 432,
        'T': 918,
        'Ix': -235,
        'M': 56,
    }

    mapping = {
        'time_received': 'time_received',
        'sensor_group': 'sensor_group',
        'id': 'sensor_id',
        'P': 'pressure',
        'T': 'temperature',
        'M': 'mask',
    }

    with pytest.raises(ValueError):
        convert(original, mapping)
