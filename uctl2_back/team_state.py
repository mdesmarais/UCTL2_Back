import json
from typing import TYPE_CHECKING, List, Optional

from uctl2_back.watched_property import WatchedProperty

if TYPE_CHECKING:
    from datetime import datetime


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

        self.current_stage: WatchedProperty = last_state.current_stage if last_state else WatchedProperty(None)
        self.rank = WatchedProperty(0)
        self.team_finished: WatchedProperty = WatchedProperty(last_state.team_finished.get_value() if last_state else False)

        self.start_time: Optional[datetime] = None
        self.covered_distance: float = 0 if last_state is None else last_state.covered_distance
        self.intermediate_times: List[datetime] = []
        self.split_times: List[int] = []
        self.stage_ranks: List[int] = []
        self.current_time_index = -1

