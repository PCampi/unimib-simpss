"""Subscriber interface file."""

from abc import ABCMeta, abstractmethod
from typing import Any

from .publisher import Publisher


class Subscriber(ABCMeta):
    """
    Subscriber interface.
    Provides method for message notification, receive.
    """

    @abstractmethod
    def set_name(self, name: str):
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, publisher: Publisher):
        raise NotImplementedError

    @abstractmethod
    def receive(self, message: Any):
        raise NotImplementedError
