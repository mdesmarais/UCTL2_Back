import time

from race_state import RaceStatus
from team import Team


class Race:

    def __init__(self, name, racePoints, checkpoints):
        self.name = name
        self.distance = 0
        self.racePoints = racePoints
        self.plainRacePoints = list((p[0], p[1]) for p in racePoints)
        self.status = RaceStatus.WAITING
        self.startTime = 0
        self.teams = {}
        self.checkpoints = checkpoints

    def addTeam(self, name, bib):
        self.teams[bib] = Team(self, bib, name)

    def toJSON(self):
        return {
            'name': self.name,
            'distance': self.distance,
            'checkpoints': self.checkpoints,
            'racePoints': self.plainRacePoints,
            'startTime': self.startTime,
            'teams': list(team.toJSON() for team in self.teams.values()),
            'status': self.status
        }

    def updateTeam(self, team, state):
        team.coveredDistance = state.coveredDistance
        team.rank = state.rank
        team.currentCheckpoint = state.currentCheckpoint