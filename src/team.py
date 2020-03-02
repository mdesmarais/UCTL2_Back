
class Team:

    def __init__(self, race, bib, name):
        self.race = race

        self.bibNumber = bib
        self.name = name
        self.oldRank = 0
        self.currentStage = 0
        self.progression = 0
        self.pace = 400

        self._coveredDistance = 0
        self._pos = self.race.plainRacePoints[0]
        self._rank = 0

    @property
    def coveredDistance(self):
        return self._coveredDistance
    
    @coveredDistance.setter
    def coveredDistance(self, coveredDistance):
        self._coveredDistance = coveredDistance
        self.progression = coveredDistance / self.race.distance

        # racePoint = (lat, lon, alt, distance from start)
        # plainRacePoint = (lat, lon)
        i = sum(len(self.race.racePoints[i]) for i in range(self.currentStage))
        currentStagePoints = self.race.racePoints[self.currentStage]
        j = 0
        while j < len(currentStagePoints) and currentStagePoints[j][3] < coveredDistance:
            j += 1
        
        self._pos = self.race.plainRacePoints[i + j]

    @property
    def pos(self):
        return self._pos

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
            'pos': self.pos
        }