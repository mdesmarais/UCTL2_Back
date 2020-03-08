import time

from race_state import RaceStatus
from team import Team


class Race:

    def __init__(self, name, racePoints, stages, tickStep):
        self.name = name
        self.distance = 0
        self.racePoints = racePoints
        self.plainRacePoints = [(item[0], item[1]) for sublist in self.racePoints for item in sublist]
        self.status = RaceStatus.WAITING
        self.startTime = 0
        self.teams = {}
        self.stages = stages
        self.tickStep = tickStep

    def addTeam(self, name, bib):
        self.teams[bib] = Team(self, bib, name)

    def toJSON(self):
        return {
            'name': self.name,
            'distance': self.distance,
            'stages': self.stages,
            'racePoints': self.racePoints,
            'startTime': self.startTime,
            'teams': list(team.toJSON() for team in self.teams.values()),
            'status': self.status,
            'tickStep': self.tickStep
        }

    def updateTeam(self, team, state):
        team.rank = state.rank
        team.currentTimeIndex = state.currentTimeIndex
        team.currentStage = state.currentStage
        team.coveredDistance = state.coveredDistance