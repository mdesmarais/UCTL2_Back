
class Team:

    def __init__(self, race, bib, name):
        self.race = race

        self.bibNumber = bib
        self.name = name
        self.oldRank = 0

        # Index of the current stage
        self.currentStage = 0

        self.stageRanks = []

        # Index of the current time (split time, intermediate time)
        self.currentTimeIndex = -1
        self.pace = 400

        self._coveredDistance = 0
        self._progression = 0
        self._pos = self.race.plainRacePoints[0]
        self._rank = 0

    @property
    def coveredDistance(self):
        return self._coveredDistance
    
    @coveredDistance.setter
    def coveredDistance(self, coveredDistance):
        self._coveredDistance = coveredDistance
        self._progression = coveredDistance / self.race.distance

        # racePoint = (lat, lon, alt, distance from start)
        # plainRacePoint = (lat, lon)

        # Computes number of racePoints from previous stages
        # If the team is in the first stage, then i equals 0
        if self.currentStage > 0:
            i = sum(len(self.race.racePoints[k]) for k in range(self.currentStage))
        else:
            i = 0

        currentStagePoints = self.race.racePoints[self.currentStage]
        j = 0

        # Counts the number of racePoints where the team has already been
        while j < len(currentStagePoints) and currentStagePoints[j][3] < coveredDistance:
            j += 1

        if j > 0:
            j -= 1
        
        self._pos = self.race.plainRacePoints[i + j]

    @property
    def lastStageRank(self):
        return self.stageRanks[self.currentTimeIndex]

    @property
    def pos(self):
        return self._pos

    @property
    def progression(self):
        return self._progression

    @property
    def rank(self):
        return self._rank
    
    @rank.setter
    def rank(self, rank):
        self.oldRank = self.rank
        self._rank = rank
    
    def toJSON(self):
        return {
            'bibNumber': self.bibNumber,
            'name': self.name,
            'rank': self.rank,
            'oldRank': self.oldRank,
            'currentStage': self.currentStage if self.currentStage >= 0 else 0,
            'coveredDistance': self.coveredDistance,
            'progression': self.progression,
            'pace': self.pace,
            'pos': self.pos,
            'stageRanks': self.stageRanks
        }