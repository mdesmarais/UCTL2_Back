
class InvalidConfigError(Exception):
    """
        Represents an error when a configuration is not valid (wrong format, invalid values, ...)
    """
    pass

class RaceError(Exception):
    """
        Exception thrown when race informations could not been read
        from the config file
    """
    pass
