"""
    This module defines the TeamState class
"""
import collections
from typing import TYPE_CHECKING, List, Optional

from uctl2_back.watched_property import WatchedProperty

if TYPE_CHECKING:
    from datetime import datetime
    from uctl2_back.stage import Stage

TransitionTime = collections.namedtuple('TransitionTime', ['split_time', 'inter_time', 'relative_index'])

class TeamState:

    """
        Represents the state of a team in a race file

        A state is a line in the race file
    """

    def __init__(self, bib_number: int, name: str, last_state: Optional['TeamState'] = None):
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

        self.current_stage: WatchedProperty = last_state.current_stage if last_state else WatchedProperty(None)
        self.rank = WatchedProperty(0)
        self.team_finished: WatchedProperty = WatchedProperty(last_state.team_finished.get_value() if last_state else False)

        self.start_time: Optional['datetime'] = None
        self.covered_distance: float = 0 if last_state is None else last_state.covered_distance
        self.intermediate_times: List['datetime'] = []
        self.split_times: List[int] = []
        self.stage_ranks: List[int] = []
        self.current_time_index = -1

    def update_covered_distance(self, stages: List['Stage'], tick_step: int, loop_time: float, default_pace: int = 300) -> None:
        """
            Updates the covered distance with an an estimated value

            If the team does not have started the race yet then 0 will be set.
            If the team is in the first state, then the default_pace parameter will
            be used. It the number of seconds for 1km.
            The the team already have finished the race, the distance from start
            of the last stage will be set.
            If the team have moved into another stage, then the distance from
            the start of the current checkpoint will be set.

            :param stages: list of stages
            :param tick_step: speed of the simulation (=1 if it is a real race)
            :param loop_time: number of seconds since the last call to the parent function
            :param default_pace: default pace in seconds (for 1km)
        """
        if default_pace <= 0:
            raise ValueError('default pace must be strictely positive')

        if self.start_time is None:
            self.covered_distance = 0
            return

        if self.team_finished.get_value():
            last_stage = stages[-1]
            self.covered_distance = last_stage.dst_from_start + last_stage.length
            return

        if len(self.split_times) == 0:
            # Default pace when we don't known each team's pace yet
            self.covered_distance += loop_time * tick_step * 1000 / default_pace
            return

        current_stage_index: int = self.current_stage.get_value()

        # Computing the covered distance since the last loop (step distance)
        if self.current_stage.has_changed:
            self.covered_distance = stages[current_stage_index].dst_from_start
        else:
            stage_dst_from_start = stages[current_stage_index].dst_from_start

            elapsed_time = self.intermediate_times[self.current_time_index] - self.start_time
            average_speed = stage_dst_from_start / elapsed_time.total_seconds()
            self.covered_distance += average_speed * loop_time * tick_step

    def update_stage_times(self, transition_times: List[TransitionTime]) -> None:
        """
            Updates times list with transition times

            Only lists :attr:`TeamState.intermediate_times`, :attr:`TeamState.split_times`, :attr:`TeamState.stage_ranks`
            are modified. The last one will be updated with 0s : we do not compute a rank for non timed stages.

            :param transition_times: transitions times to add for the given state
        """
        for i, transition_time in enumerate(transition_times):
            self.intermediate_times.insert(transition_time.relative_index + i, transition_time.inter_time)
            self.split_times.insert(transition_time.relative_index + i, transition_time.split_time)
            self.stage_ranks.insert(transition_time.relative_index + i, 0)
