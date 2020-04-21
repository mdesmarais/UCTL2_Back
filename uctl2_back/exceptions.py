
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

class RaceFileFieldError(Exception):
    """
        Exception thrown when there were an error while
        retreiving a column from a row of a race file.
    """
    pass
