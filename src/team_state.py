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

        self._currentSegment = -1
        self._rank = 0
        self._segmentDistanceFromStart = 0
        self._stepDistance = 0
        self._coveredDistance = 0 if lastState is None else lastState.coveredDistance

        self.pace = 0

        self.coveredDistanceChanged = False
        self.currentSegmentChanged = False
        self.rankChanged = False
        self.stepDistanceChanged = False
        self.segmentDistanceFromStartChanged = False
        self.statusChanged = False

    @property
    def coveredDistance(self):
        return self._coveredDistance

    @coveredDistance.setter
    @stateProperty('coveredDistance', 'coveredDistanceChanged')
    def coveredDistance(self, coveredDistance):
        self._coveredDistance = coveredDistance

    @property
    def currentSegment(self):
        return self._currentSegment
    
    @currentSegment.setter
    @stateProperty('currentSegment', 'currentSegmentChanged')
    def currentSegment(self, currentSegment):
        self._currentSegment = currentSegment

    @property
    def oldRank(self):
        if self.lastState is None:
            return self.rank
        else:
            return self.lastState.rank

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

    @property
    def segmentDistanceFromStart(self):
        return self._segmentDistanceFromStart

    @segmentDistanceFromStart.setter
    @stateProperty('segmentDistanceFromStart', 'segmentDistanceFromStartChanged')
    def segmentDistanceFromStart(self, sdfs):
        self._segmentDistanceFromStart = sdfs

    @property
    def stepDistance(self):
        return self._stepDistance

    @stepDistance.setter
    @stateProperty('stepDistance', 'stepDistanceChanged')
    def stepDistance(self, stepDistance):
        self._stepDistance = stepDistance
