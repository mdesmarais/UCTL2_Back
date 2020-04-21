import time
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from uctl2_back.race_state import RaceStatus
from uctl2_back.team import Team

if TYPE_CHECKING:
    from uctl2_back.stage import Stage
    from uctl2_back.uctl2_setup import PointsWithDistance


class Race:

    def __init__(self, name: str, racepoints: List['PointsWithDistance'], stages: List['Stage'], tick_step: int) -> None:
        """
            Creates a new race

            The size of racepoints must be equal to the size of stages
            A ValueError exception will be raised if it is not the case.

            The tick_step parameter is used in the case of a simulated race.
            It represents the number of of simulated seconds for one second.
            In a real race, this parameter equals 1.
            The tick_step must be strictely positive.

            :param name: name of the race
            :param racepoints: gps points grouped by stages
            :param stages: list of stages
            :param tick_step: speed of the race (equals to 1 when it is a real race)
            :raises ValueError: if a stage is not associated to a list of racepoints
            :raises ValueError: if tick_step is negative
        """
        if not len(racepoints) == len(stages):
            raise ValueError('each stage must be associted to a list of racepoints')

        if tick_step <= 0:
            raise ValueError('tick step must be strictely positive')

        self.name = name
        self.distance = 0
        self.racepoints = racepoints
        self.plain_racepoints = [(item[0], item[1]) for sublist in self.racepoints for item in sublist]
        self.status = RaceStatus.WAITING
        self.startTime: int = 0
        self.teams: Dict[int, Team] = {}
        self.stages = stages
        self.length = sum(stage.length for stage in stages if stage.is_timed)
        self.tick_step = tick_step

    def add_team(self, bib: int, name: str) -> None:
        """
            Adds a new team

            :param bib: bib number, should be unique and strictely positive
            :param name: name of the team
        """
        self.teams[bib] = Team(self, bib, name)

    def reset_teams(self) -> None:
        """
            Resets teams to their default state

            By resetting teams, progressions, covered distance,
            current stage index are set to default value.

            A new instance of class Team is created to achieve that.
        """
        for bib in self.teams.keys():
            self.teams[bib] = Team(self, bib, self.teams[bib].name)

    def serialize(self) -> Dict[str, Any]:
        """
            Serializes instance

            :return: serialized instance
        """
        return {
            'name': self.name,
            'distance': self.distance,
            'stages': [stage.serialize() for stage in self.stages],
            'racePoints': self.racepoints,
            'startTime': self.startTime,
            'teams': list(team.serialize() for team in self.teams.values()),
            'status': self.status,
            'tickStep': self.tick_step
        }

