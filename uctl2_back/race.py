import time
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from uctl2_back.race_state import RaceStatus
from uctl2_back.team import Team

if TYPE_CHECKING:
    from uctl2_back.stage import Stage
    from uctl2_back.uctl2_setup import PointsWithDistance


class Race:

    def __init__(self, name: str, racepoints: List['PointsWithDistance'], stages: List['Stage'], tickStep: int):
        self.name = name
        self.distance = 0
        self.racepoints = racepoints
        self.plain_racepoints = [(item[0], item[1]) for sublist in self.racepoints for item in sublist]
        self.status = RaceStatus.WAITING
        self.startTime = 0
        self.teams: Dict[int, Team] = {}
        self.stages = stages
        self.length = sum(stage.length for stage in stages if stage.is_timed)
        self.tickStep = tickStep

    def addTeam(self, name, bib):
        self.teams[bib] = Team(self, bib, name)

    def resetTeams(self):
        for bib in self.teams.keys():
            self.teams[bib] = Team(self, bib, self.teams[bib].name)

    def serialize(self):
        return {
            'name': self.name,
            'distance': self.distance,
            'stages': [stage.serialize() for stage in self.stages],
            'racePoints': self.racepoints,
            'startTime': self.startTime,
            'teams': list(team.serialize() for team in self.teams.values()),
            'status': self.status,
            'tickStep': self.tickStep
        }

    def updateTeam(self, team, state):
        team.rank = state.rank
        team.currentTimeIndex = state.currentTimeIndex
        team.currentStage = state.currentStage
        team.coveredDistance = state.coveredDistance
        team.stageRanks = state.stageRanks
