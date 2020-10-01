import csv
import re
import sys
from datetime import datetime

import splinter
from funcoperators import to
from toolz import first, keymap, valmap, groupby


def parse_winner(winner):
    try:
        return {'b': 'blue', 'r': 'red', '': ''}[winner.lower()[0]]
    except:
        raise ValueError(f'Expected "blue"/"red" or "b"/"r" or nothing for draw, got {winner}')


def parse_teams(teams):
    pattern = re.compile('\s*(red|blue):([^$]*)$', flags=re.IGNORECASE)
    result = dict(
        pattern.findall(line) | to(list) | to(first)
        for line in teams.split('\n')
        if pattern.match(line)
    )
    result = keymap(str.lower, result)
    result = valmap(lambda x: [y.strip() for y in x.split(',')], result)
    return result


def get_teams():
    executable_path = './chromedriver'
    with splinter.Browser('chrome', executable_path=executable_path) as browser:
        browser.visit("https://www.meetup.com/Ijburg-Futsal-Regulars/events/past/")
        last_event = browser.find_by_css('.eventCard--link').first['href']
        browser.visit(last_event)
        date = browser.find_by_tag('time')['datetime'][:-3] | to(int)  # strip milliseconds
        teams = browser.find_by_css('.comment-content').text
        return datetime.utcfromtimestamp(date).date(), parse_teams(teams)


def get_results():
    with open('results.csv') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)  # skip headers
        # group by date
        results = groupby(lambda x: x[0], reader | to(list))
        results = keymap(lambda x: datetime.strptime(x, '%Y-%m-%d').date(), results)
        return results


def get_points(team, winner):
    if winner == team:
        return 3
    elif winner == '':
        return 1
    else:
        return 0


def main(winner):

    date, teams = get_teams()
    winner = parse_winner(winner)
    results = get_results()

    results[date] = [
        [date.strftime('%Y-%m-%d'), player, team, get_points(team, winner)]
        for team, players in teams.items()
        for player in players
    ]
    with open('results.csv', 'w') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['date', 'player', 'team', 'points'])
        writer.writerows(
            row
            for date, rows in results.items()
            for row in rows
        )


if __name__ == "__main__":
    main(sys.argv[1])