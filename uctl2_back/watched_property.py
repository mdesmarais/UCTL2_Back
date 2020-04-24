"""
    This module defines the WatchedProperty class
"""
from typing import Optional, TypeVar

# Type aliases
T = TypeVar('T')

class WatchedProperty:

    """
        Represents a property with a boolean to indicate
        if it has been modified.
    """

    def __init__(self, initial_value: Optional[T] = None) -> None:
        self._value = initial_value
        self._old_value: Optional[T] = initial_value

    def __eq__(self, o):
        return self._value == o

    def get_value(self) -> T:
        """
            Gets the value of a property

            The property must have been initialized before

            :return: value of the property
            :raises ValueError: if the property is not initialized
        """
        if not self._value is None:
            return self._value

        raise ValueError('property is not initialized')

    @property
    def has_changed(self) -> bool:
        """ Checks if the property has a new value """
        return not self._value == self._old_value

    def set_value(self, value: T) -> None:
        """
            Sets a new value for the property

            If the new value is different than the current
            then a call to :attr:`has_changed` will give True.

            :param value: new value of the property
        """
        self._old_value = self._value
        self._value = value
