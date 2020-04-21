import json
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from datetime import datetime


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

    def __init__(self, bib_number: int, name: str, last_state: Optional['TeamState']=None):
        """
            Creates a new team state

            A team state represents a line in a race file.
            The last_state parameter is used to keep old values.

            :param bib_number: bib number of the team
            :param name: name of the team
            :param last_state: previous state from the last reading, could be None
            :raises ValueError: if bib_number if negative
        """
        if bib_number <= 0:
            raise ValueError('bib_number must be strictely positive')

        self.bib_number = bib_number
        self.name = name
        self.lastState = last_state

        self._current_stage = -1
        self._rank = 0
        self._team_finished = False

        self.start_time: Optional[datetime] = None
        self.covered_distance: float = 0 if last_state is None else last_state.covered_distance
        self.intermediate_times: List[datetime] = []
        self.split_times: List[int] = []
        self.stage_ranks: List[int] = []
        self.current_time_index = -1

        self.current_stage_changed = False
        self.rank_changed = False
        self.team_finished_changed = False

    @property
    def current_stage(self):
        return self._current_stage
    
    @current_stage.setter
    @stateProperty('current_stage', 'current_stage_changed')
    def current_stage(self, current_stage):
        self._current_stage = current_stage
    
    @property
    def rank(self):
        return self._rank

    @rank.setter
    @stateProperty('rank', 'rank_changed')
    def rank(self, rank):
        b = self._rank == 0
        self._rank = rank

        if b:
            self.rank_changed = False
    
    @property
    def team_finished(self):
        return self._team_finished

    @team_finished.setter
    @stateProperty('team_finished', 'team_finished_changed')
    def team_finished(self, team_finished):
        self._team_finished = team_finished
