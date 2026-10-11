"""After a run: which countries want a look, and why.

    python tools/report.py <run id>

Reads the published index and every country's manifest, and the run's jobs
from GitHub's public API (a few requests, well inside the unauthenticated
limit), and lists the countries that failed, that came out as one region or
as more than 150, and those whose build warned that places fell in no region.
"""

import json
import sys
import urllib.request

DATA = 'https://happyroads.data.tumeechu.com/v1'
API = 'https://api.github.com/repos/Jamitheone-git/Happy-Roads-Data'


def _get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'HappyRoads report'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _jobs(run):
    jobs, page = [], 1
    while True:
        found = _get(f'{API}/actions/runs/{run}/jobs?per_page=100&page={page}')['jobs']
        jobs += found
        if len(found) < 100:
            return jobs
        page += 1


def main(run):
    jobs = [j for j in _jobs(run) if j['name'].startswith('build')]
    failed = sorted(j['name'].split('(')[1].split(',')[0] for j in jobs
                    if j['conclusion'] != 'success')

    # Every job carries one notice about the runner image; more than one is a
    # warning of our own, which only the drop check writes.
    warned = []
    suite = _get(f'{API}/actions/runs/{run}')['check_suite_id']
    page = 1
    while True:
        runs = _get(f'{API}/check-suites/{suite}/check-runs?per_page=100&page={page}')['check_runs']
        for check in runs:
            if check['output']['annotations_count'] > 1 and check['name'].startswith('build'):
                for note in _get(f"{API}/check-runs/{check['id']}/annotations"):
                    if 'fell in no region' in note['message']:
                        warned.append(note['message'])
        if len(runs) < 100:
            break
        page += 1

    index = _get(f'{DATA}/index.json')
    one, many, sizes = [], [], {}
    for country in index['countries']:
        regions = _get(f"{DATA}/{country['manifest']}")['regions'][1:]
        sizes[country['id']] = len(regions)
        if len(regions) == 1:
            one.append(country['id'])
        elif len(regions) > 150:
            many.append(f"{country['id']} ({len(regions)})")

    print(f"{len(index['countries'])} countries published, {len(jobs)} built this run")
    print(f"failed ({len(failed)}): {', '.join(failed) or '-'}")
    print(f"one region ({len(one)}): {', '.join(one) or '-'}")
    print(f"over 150 regions ({len(many)}): {', '.join(many) or '-'}")
    print(f"places lost ({len(warned)}):")
    for line in sorted(warned):
        print(f'  {line}')


if __name__ == '__main__':
    main(sys.argv[1])
