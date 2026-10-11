"""Download one country's files for its build job, and say where they are:
python -m happyroads_data.fetch --entry '<one matrix entry>' --dir extracts

Writes <dir>/fetched.json, which `build --fetched` reads. In Python rather
than the workflow's shell, so that what a job downloads is tested."""

import argparse
import json
import subprocess
from pathlib import Path


def _curl(url, path):
    subprocess.run(['curl', '-fsSL', '--retry', '3', '-o', str(path), url], check=True)


def fetch(entry, folder, download=_curl):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    def get(url):
        path = folder / url.rsplit('/', 1)[-1]
        download(url, path)
        return str(path)

    fetched = {
        'name': entry.get('name'),
        'extracts': [get(url) for url in entry.get('extracts', [])],
        'outlines': [get(url) for url in entry.get('outlines', [])],
        'parts': [{'id': part['id'], 'name': part['name'], 'code': part.get('code'),
                   'pbf': get(part['pbf']), 'poly': get(part['poly'])}
                  for part in entry.get('parts', [])],
    }
    (folder / 'fetched.json').write_text(json.dumps(fetched), encoding='utf-8')
    return fetched


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--entry', required=True, help='one matrix entry, as JSON')
    parser.add_argument('--dir', required=True)
    args = parser.parse_args(argv)
    fetch(json.loads(args.entry), args.dir)


if __name__ == '__main__':
    main()
