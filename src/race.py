import time

from race_state import RaceStatus


class Race:

    def __init__(self, name, racePoints):
        self.name = name
        self.distance = 0
        self.racePoints = racePoints
        self.plainRacePoints = list((p[0], p[1]) for p in racePoints)
        self.status = RaceStatus.WAITING
        self.startTime = 0
        self.teams = []

    def addTeam(self, name, bib, pace):
        self.teams.append({
            'name': name,
            'bibNumber': bib,
            'pace': pace,
            'pos': self.plainRacePoints[0]
        })

    def toJSON(self):
        return {
            'name': self.name,
            'distance': self.distance,
            'status': self.status,
            'racePoints': self.plainRacePoints,
            'startTime': self.startTime,
            'teams': self.teams
        }
