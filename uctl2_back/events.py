"""
    This modules defines constants for events and
    functions to create them.
"""
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from uctl2_back.race import Race
    from uctl2_back.team import Team
    from uctl2_back.team_state import TeamState


RACE_SETUP = 0

RACE_STATUS = 1

TEAM_START = 2
TEAM_CHECKPOINT = 3
TEAM_END = 4

TEAM_OVERTAKE = 5


def create_team_end_race_event(race: 'Race', team_state: 'TeamState') -> Dict[str, Any]:
    """
        Creates an event for notifying that team finished the race

        :param race: instance of the current race
        :param team_state: the last state of the team
        :return: the event
    """
    # totalTime = sum of split times for timed stages only
    total_time = sum((x for i, x in enumerate(team_state.split_times) if race.stages[i].is_timed))
    average_pace = total_time * 1000 / race.length

    return {
        'id': TEAM_END,
        'payload': {
            'bibNumber': team_state.bib_number,
            'totalTime': total_time,
            'averagePace': average_pace
        }
    }


def create_team_end_stage_event(team: 'Team', team_state: 'TeamState') -> Dict[str, Any]:
    """
        Creates an event for notifying that team finished a stage

        The team must have started the race (start_time != None) and
        one split time.

        :param team: instance of the team
        :param team_state: the last state of the team
        :return: the event
    """
    if not team_state.start_time:
        raise ValueError('')

    last_split_time = team_state.split_times[team.current_time_index]
    # Pace computation : Xs * 1000m / segment distance (in meters)
    average_pace = last_split_time * 1000 / team.race.stages[team.current_stage_index - 1].length

    return {
        'id': TEAM_CHECKPOINT,
        'payload': {
            'bibNumber': team.bib_number,
            'currentStage': team.current_stage_index,
            'lastStage': team.current_stage_index - 1,
            'splitTime': last_split_time,
            'averagePace': average_pace,
            'coveredDistance': team.covered_distance,
            'pos': list(team.current_location),
            'stageRank': team.last_stage_rank
        }
    }


def create_team_rank_event(team: 'Team') -> Dict[str, Any]:
    """
        Creates an event for notifying that team overtaken one or more teams

        :param team: instance of the team
        :return: the event
    """
    return {
        'id': TEAM_OVERTAKE,
        'payload': {
            'bibNumber': team.bib_number,
            'oldRank': team.old_rank,
            'rank': team.rank,
            'teams': team.compute_overtaken_teams(team.race.teams.values())
        }
    }
