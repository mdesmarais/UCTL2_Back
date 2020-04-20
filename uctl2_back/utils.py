from typing import Any, Dict


class InvalidConfigError(Exception):
    """
        Represents an error when a configuration is not valid (wrong format, invalid values, ...)
    """
    pass

class Serializable:

    def serialize(self) -> Dict[str, Any]: raise NotImplementedError('serialized method is not implemented')
