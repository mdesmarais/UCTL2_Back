"""
    This modules defines the Team class
"""
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Tuple

if TYPE_CHECKING:
    from uctl2_back.race import Race
    from uctl2_back.team_state import TeamState


class Team:

    """
        Represents a Team during a race

        A team is set by a unique bib number and a name.
    """

    def __init__(self, race: 'Race', bib: int, name: str) -> None:
        """
            Creates a new team

            :param race: an instance of the race where the team is participating
            :param bib: bib number
            :param name: name of the team
        """
        self.race = race

        self.bib_number = bib
        self.name = name
        self.old_rank: int = 0
        self.stage_ranks: List[int] = []
        self.pace: int = 400

        # Index of the current stage
        self.current_stage_index: int = 0

        # Index of the current time (split time, intermediate time)
        self.current_time_index: int = -1

        self._covered_distance: float = 0
        self._progression: float = 0
        self._current_location: Tuple[float, float] = self.race.plain_racepoints[0] if len(self.race.plain_racepoints) > 0 else (0, 0)
        self._rank: int = 0

    def compute_overtaken_teams(self, teams: Iterable['Team']) -> List[int]:
        """
            Computes overtaken teams when team has a new rank

            :param teams: list of teams in the race
            :return: list of team bibs
        """
        overtaken_teams = []

        for team in teams:
            if not self.bib_number == team.bib_number and self.old_rank > team.old_rank and self.rank < team.rank:
                overtaken_teams.append(team.bib_number)

        return overtaken_teams

    @property
    def current_location(self) -> Tuple[float, float]:
        """ Gets the current gps position of the team """
        return self._current_location

    @property
    def covered_distance(self) -> float:
        """ Get the covered distance (in meters) """
        return self._covered_distance

    @covered_distance.setter
    def covered_distance(self, covered_distance: float) -> None:
        """
            Sets the covered distance

            The progression of the team will be updated as well
            as the current_location.

            :param coveredDistance: new covered distance (in meters)
            :raises ValueError: if covered_distance is negative
        """
        if covered_distance < 0:
            raise ValueError('covered distance must be positive')

        self._covered_distance = covered_distance
        self._progression = covered_distance / self.race.distance

        # racepoint = (lat, lon, alt, distance from start)
        # plain_racepoint = (lat, lon)

        # Computes number of racePoints from previous stages
        # If the team is in the first stage, then i equals 0
        if self.current_stage_index > 0:
            i = sum(len(self.race.racepoints[k]) for k in range(self.current_stage_index))
        else:
            i = 0

        current_stagepoints = self.race.racepoints[self.current_stage_index]
        j = 0

        # Counts the number of racepoints where the team has already been
        while j < len(current_stagepoints) and current_stagepoints[j][3] <= covered_distance:
            j += 1

        if j > 0:
            j -= 1

        self._current_location = self.race.plain_racepoints[i + j]

    @property
    def last_stage_rank(self) -> int:
        """ Get the rank for the last stage """
        return self.stage_ranks[self.current_time_index]

    @property
    def progression(self) -> float:
        """ Get the race progression (between 0 and 1) """
        return self._progression

    @property
    def rank(self) -> int:
        """ Gets the rank of the team """
        return self._rank

    @rank.setter
    def rank(self, rank):
        """
            Sets a new rank

            :param rank: new rank of the team
            :raises ValueError: if the rank is negative or null
        """
        if rank <= 0:
            raise ValueError('rank must be strictely positive')

        self.old_rank = self._rank
        self._rank = rank

    def serialize(self) -> Dict[str, Any]:
        """
            Serializes the instance

            :return serialized instance as a dict
        """
        return {
            'bibNumber': self.bib_number,
            'name': self.name,
            'rank': self.rank,
            'oldRank': self.old_rank,
            'currentStage': self.current_stage_index if self.current_stage_index >= 0 else 0,
            'coveredDistance': self.covered_distance,
            'progression': self.progression,
            'pace': self.pace,
            'pos': self.current_location,
            'stageRanks': self.stage_ranks
        }

    def update_from_state(self, state: 'TeamState') -> None:
        """
            Updates team fields from a team state

            A team state is computed after each reading of
            the race file.

            :param state: computed team state
        """
        self.current_time_index = state.current_time_index
        self.current_stage_index = state.current_stage.get_value()
        self.covered_distance = state.covered_distance
        self.stage_ranks = state.stage_ranks
