"""Interface for publishers."""

from abc import ABCMeta, abstractmethod
from typing import Any

from .subscriber import Subscriber


class Publisher(ABCMeta):
    """
    Publisher interface.
    """

    @abstractmethod
    def add_subscriber(self, sub_obj: Subscriber, sub_name: str):
        raise NotImplementedError

    @abstractmethod
    def remove_subscriber(self, name):
        raise NotImplementedError

    @abstractmethod
    def publish(self, message: Any):
        raise NotImplementedError
