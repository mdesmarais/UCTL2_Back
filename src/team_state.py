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

        self._currentStage = -1
        self._rank = 0

        self.startTime = None
        self.coveredDistance = 0 if lastState is None else lastState.coveredDistance
        self.intermediateTimes = []
        self.splitTimes = []
        self.stageRanks = []
        self.currentTimeIndex = -1

        self.currentStageChanged = False
        self.rankChanged = False

    @property
    def currentStage(self):
        return self._currentStage
    
    @currentStage.setter
    @stateProperty('currentStage', 'currentStageChanged')
    def currentStage(self, currentStage):
        self._currentStage = currentStage
    
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