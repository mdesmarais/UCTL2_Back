
class InvalidConfigError(Exception):
    """
        Represents an error when a configuration is not valid (wrong format, invalid values, ...)
    """
    pass

class RaceEmptyError(Exception):
    """
        Exception raised when the race file is empty
    """
    pass

class RaceError(Exception):
    """
        Exception raised when race informations could not been read
        from the config file
    """
    pass

class RaceFileFieldError(Exception):
    """
        Exception raised when there were an error while
        retreiving a column from a row of a race file.
    """
    pass
