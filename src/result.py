import json
import re
import sys
from datetime import datetime
from pathlib import Path

import splinter
from funcoperators import to, filterwith
from toolz import first, keymap, valmap, groupby, count


DIR = Path(__file__).parent


if __name__ == "__main__":

    winner = sys.argv[1]
    date = sys.argv[2] | to(int) if len(sys.argv) > 2 else 0

    # region Get teams / Event date
    executable_path = DIR / '../bin/chromedriver'
    with splinter.Browser('chrome', executable_path=executable_path) as browser:
        browser.visit("https://www.meetup.com/Ijburg-Futsal-Regulars/events/past/")
        event = (browser.find_by_css('.eventCard--link') | to(list))[date]
        browser.visit(event['href'])
        date = browser.find_by_tag('time')['datetime'][:-3] | to(int)  # strip milliseconds
        for comment in browser.find_by_css('.comment-content'):
            if 'Teams for' in comment.text:
                teams = comment.text
                break
        else:
            raise ValueError('No teams comment found')

    pattern = re.compile('\s*(red|blue):([^$]*)$', flags=re.IGNORECASE)
    teams = dict(
        pattern.findall(line) | to(list) | to(first)
        for line in teams.split('\n')
        if pattern.match(line)
    )
    teams = keymap(str.title, teams)
    teams = valmap(lambda x: [y.strip() for y in x.split(',')], teams)
    date = datetime.utcfromtimestamp(date).date()
    # endregion

    # region Update matches
    winner = {'b': 'Blue', 'r': 'Red', 'd': 'Draw'}[winner]
    with open(DIR/'../data/matches.json') as f:
        matches = json.load(f)
        matches_by_date = groupby(lambda x: x['date'], matches | to(list))
        matches_by_date = keymap(lambda x: datetime.strptime(x, '%Y-%m-%d').date(), matches_by_date)

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
        records = [match for date, matches in matches_by_date.items() for match in matches]
        json.dump(sorted(records, key=lambda x: x['date'], reverse=True), f, indent=2)
    # endregion

    # region Update stats
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
            for name, games in groupby(lambda x: x['name'], records).items()
        ]
        json.dump(sorted(stats, key=lambda x: x['pointsPerGame'], reverse=True), f, indent=2)
    # endregion

