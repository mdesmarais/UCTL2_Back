
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

        self.pace = -1
        self.segments = 0
        self.segmentDistanceFromStart = 0

        self.rank = 0

        self.paceChanged = False
        self.segmentsChanged = False
        self.segmentDistanceFromStartChanged = False
        self.rankChanged = False

    @stateProperty('pace', 'paceChanged')
    def setPace(self, pace):
        self.pace = pace

    @stateProperty('rank', 'rankChanged')
    def setRank(self, rank):
        self.rank = rank

    @stateProperty('segments', 'segmentsChanged')
    def setSegments(self, segments):
        self.segments = segments
    
    @stateProperty('stepDistance', 'stepDistanceChanged')
    def setStepDistance(self, stepDistance):
        self.stepDistance = stepDistance

    @stateProperty('segmentDistanceFromStart', 'segmentDistanceFromStartChanged')
    def setSegmentDistanceFromStart(self, segmentDistanceFromStart):
        self.segmentDistanceFromStart = segmentDistanceFromStart
    
    def stateChanged(self):
        return self.paceChanged or self.segmentsChanged or self.segmentDistanceFromStart or self.rankChanged()
    
    def debug(self):
        print('paceChanged=%s segmentsChanged=%s segmentDistanceFromStart=%s rankChanged=%s' % (self.paceChanged, self.segmentsChanged, self.segmentDistanceFromStartChanged, self.rankChanged))

    def oldRank(self):
        if self.lastState is None:
            return self.rank
        else:
            return self.lastState.rank

