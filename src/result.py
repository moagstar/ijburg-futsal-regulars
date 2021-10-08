import json
import re
import sys
import datetime
import typing
from pathlib import Path
from typing import Tuple, List, Any, Dict

import splinter
from funcoperators import to, filterwith
from toolz import first, keymap, valmap, groupby, count


DIR = Path(__file__).parent


class Teams(typing.TypedDict):
    Red: List[str]
    Blue: List[str]


def get_teams(event_comment: str) -> Teams:
    """
    Parse the event comment to figure out who was playing on which team.

    :param event_comment: The comment from meetup saying what the teams are.

    :return: Teams dict with 'Red' and 'Blue' keys, the values are lists of
             player names.
    """
    pattern = re.compile('\s*(red|blue):([^$]*)$', flags=re.IGNORECASE)
    teams = dict(
        pattern.findall(line) | to(list) | to(first)
        for line in event_comment.split('\n')
        if pattern.match(line)
    )
    teams = keymap(str.title, teams)
    teams = valmap(lambda x: [y.strip() for y in x.split(',')], teams)

    return teams


def get_event(offset: int) -> Tuple[datetime.date, str]:
    """
    Scrape the event from meetup comments.

    :param offset: Which event to get, i.e. 0 == this week, -1 last week etc.

    :return: Tuple of the date of the event and the text of the comment
             containing the teams.
    """
    executable_path = DIR / '../bin/chromedriver'
    with splinter.Browser('chrome', executable_path=executable_path) as browser:
        browser.visit("https://www.meetup.com/Ijburg-Futsal-Regulars/events/past/")
        event_el = (browser.find_by_css('.eventCard--link') | to(list))[offset]
        browser.visit(event_el['href'])
        date = browser.find_by_tag('time')['datetime'][:-3] | to(int)  # strip milliseconds
        for comment in browser.find_by_css('.comment-content'):
            if 'Teams for' in comment.text:
                event = comment.text
                break
        else:
            raise ValueError('No teams comment found')
    date = datetime.datetime.utcfromtimestamp(date).date()

    return date, event


class PlayerMatch(typing.TypedDict):
    date: datetime.date
    name: str
    team: str
    points: int


def update_matches(date: datetime.date, teams: Teams, winner: typing.Literal['r', 'b', 'd']) -> List[PlayerMatch]:
    """
    Update the matches json file containing a history of the matches that were
    played. If the match for a particular date already exists those values are
    overwritten with the new values.

    :param date: Date that the match took place.
    :param teams: Which players played on which colour team.
    :param winner: Which team was the winner (or draw)

    :return: The records from all matches that have been played.
    """
    winner = {'b': 'Blue', 'r': 'Red', 'd': 'Draw'}[winner]

    with open(DIR/'../data/matches.json') as f:
        matches = json.load(f)
        matches_by_date = groupby(lambda x: x['date'], matches | to(list))
        matches_by_date = keymap(
            lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').date(),
            matches_by_date,
        )

    matches_by_date[date] = [
        {
            'date': date.strftime('%Y-%m-%d'),
            'name': name,
            'team': team,
            'points': {team: 3, 'Draw': 1}.get(winner, 0),
        }
        for team, names in teams.items()
        for name in names
    ]

    with open(DIR/'../data/matches.json', 'w') as f:
        matches = [match for date, matches in matches_by_date.items() for match in matches]
        json.dump(sorted(records, key=lambda x: x['date'], reverse=True), f, indent=2)

    return matches


def update_stats(matches: List[PlayerMatch]):
    """
    Update the statistics file based on the played matches.
    """
    with open(DIR/'../data/stats.json', 'w') as f:
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
        json.dump(sorted(stats, key=lambda x: x['pointsPerGame'], reverse=True), f, indent=2)


if __name__ == "__main__":

    winner = sys.argv[1]
    offset = sys.argv[2] | to(int) if len(sys.argv) > 2 else 0
    date, event_comment = get_event(offset=offset)
    
    event_comment = """
        
    """; date = datetime.date(2021, 9, 1)

    teams = get_teams(event_comment)
    records = update_matches(date, teams, winner)
    update_stats(records)
