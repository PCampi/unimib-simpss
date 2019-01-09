"""Base storage interface file."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseStorage(ABC):
    """
    This class should be used as an interface and subclassed
    by implementors.
    """

    @abstractmethod
    def connect(self):
        """Connect to storage backend."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self):
        raise NotImplementedError

    @abstractmethod
    def create_database(self, db_name: str, replication: int):
        raise NotImplementedError

    @abstractmethod
    def create_table(self, table_name: str, primary_key: Tuple[str, str],
                     columns: Dict[str, str]):
        raise NotImplementedError

    @abstractmethod
    def insert_row(self, row: Dict[str, Any]):
        raise NotImplementedError
