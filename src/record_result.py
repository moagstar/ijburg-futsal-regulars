import json
import datetime
import typing
from io import StringIO

import yaml
from pathlib import Path
from munch import munchify

from funcoperators import to, filterwith
from toolz import keymap, groupby, count


DIR = Path(__file__).parent


class Teams(typing.TypedDict):
    Red: list[str]
    Blue: list[str]


class PlayerMatch(typing.TypedDict):
    date: datetime.date
    name: str
    team: str
    points: int


def update_matches(matches, match) -> list[PlayerMatch]:
    """
    Update the matches json file containing a history of the matches that were
    played. If the match for a particular date already exists those values are
    overwritten with the new values.

    :param date: Date that the match took place.
    :param teams: Which players played on which colour team.
    :param winner: Which team was the winner (or draw)

    :return: The records from all matches that have been played.
    """
    matches_by_date = groupby(lambda x: x['date'], matches | to(list))
    matches_by_date = keymap(
        lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').date(),
        matches_by_date,
    )

    matches_by_date[match.Date] = [
        {
            'date': match.Date.strftime('%Y-%m-%d'),
            'name': name,
            'team': team,
            'points': {team: 3, 'Draw': 1}.get(match.Result, 0),
        }
        for team, names in match.Teams.items()
        for name in names
    ]

    matches = [match for date, matches in matches_by_date.items() for match in matches]
    return sorted(matches, key=lambda x: x['date'], reverse=True)


def update_stats(matches: list[PlayerMatch]):
    """
    Update the statistics file based on the played matches.
    """
    stats = [
        {
            'name': name,
            'played': len(games),
            'red':  games | filterwith(lambda x: x['team'] == 'Red') | to(count),
            'blue':  games | filterwith(lambda x: x['team'] == 'Blue') | to(count),
            'wins': games | filterwith(lambda x: x['points'] == 3) | to(count),
            'draw': games | filterwith(lambda x: x['points'] == 1) | to(count),
            'lose': games | filterwith(lambda x: x['points'] == 0) | to(count),
            'points': sum(x['points'] | to(int) for x in games),
            'pointsPerGame': round(
                (sum(x['points'] | to(int) for x in games) | to(float)) / len(games),
                1,
            ),
        }
        for name, games in groupby(lambda x: x['name'], matches).items()
    ]
    return sorted(stats, key=lambda x: x['pointsPerGame'], reverse=True)


if __name__ == "__main__":

    # scrape the teams if we are not pasting the comment here
    with StringIO("""
Date: 2023-09-06
Teams:
    Red: [Alex, Alex Rosu, Fatih Karagoz, Hassan El Azzouzi, Niccolò Barberis, Yannis Zervos]
    Blue: [Alex Smorodin, Ali Yadegari, Daniel Bradburn, Marco Gualandri, Mateus Gemignani, Taco]
Result: Blue
Score: 18-6
    """) as f:
        match = munchify(yaml.safe_load(f))

    # season starts in september (9th month)
    season = str(match.Date.year - (1 if match.Date.month < 9 else 0))
    season = f'{season}-{int(season[-2:]) + 1}'

    # load the existing matches for this season
    with open(f'data/{season}/matches.json') as f:
        matches = json.load(f)
        matches = update_matches(matches, match)
    with open(f'data/{season}/matches.json', 'w') as f:
        json.dump(matches, f, indent=2)

    # update the stats for this season
    stats = update_stats(matches)
    with open(f'data/{season}/stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
