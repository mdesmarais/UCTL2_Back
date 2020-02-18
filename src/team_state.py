import json


def stateProperty(attr, status):
    def wrap(func):
        def wrapper(*args, **kwargs):
            func(*args)
            lastState = getattr(args[0], 'lastState')
            if lastState is not None and not getattr(lastState, attr) == getattr(args[0], attr):
                setattr(args[0], status, True)
        return wrapper
    return wrap

class TeamState:

    def __init__(self, bibNumber, name, lastState=None):
        self.bibNumber = bibNumber
        self.name = name
        self.lastState = lastState

        self._currentCheckpoint = -1
        self._rank = 0
        self._coveredDistance = 0 if lastState is None else lastState.coveredDistance

        self.pace = 0

        self.coveredDistanceChanged = False
        self.currentCheckpointChanged = False
        self.rankChanged = False

    @property
    def coveredDistance(self):
        return self._coveredDistance

    @coveredDistance.setter
    @stateProperty('coveredDistance', 'coveredDistanceChanged')
    def coveredDistance(self, coveredDistance):
        self._coveredDistance = coveredDistance

    @property
    def currentCheckpoint(self):
        return self._currentCheckpoint
    
    @currentCheckpoint.setter
    @stateProperty('currentCheckpoint', 'currentCheckpointChanged')
    def currentCheckpoint(self, currentCheckpoint):
        self._currentCheckpoint = currentCheckpoint

    @property
    def rank(self):
        return self._rank

    @rank.setter
    @stateProperty('rank', 'rankChanged')
    def rank(self, rank):
        b = self._rank == 0
        self._rank = rank

        if b:
            self.rankChanged = False