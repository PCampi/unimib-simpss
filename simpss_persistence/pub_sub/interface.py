"""Interface for publishers."""

from abc import ABC, abstractmethod
from typing import Any


class Publisher(ABC):
    """
    Publisher interface.
    """

    @abstractmethod
    def add_subscriber(self, sub_obj, sub_name: str):
        raise NotImplementedError

    @abstractmethod
    def remove_subscriber(self, name):
        raise NotImplementedError

    @abstractmethod
    def publish(self, message: Any):
        raise NotImplementedError


class Subscriber(ABC):
    """
    Subscriber interface.
    """

    @abstractmethod
    def set_subscriber_name(self, name: str):
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, publisher):
        raise NotImplementedError

    @abstractmethod
    def receive(self, message: Any):
        raise NotImplementedError
