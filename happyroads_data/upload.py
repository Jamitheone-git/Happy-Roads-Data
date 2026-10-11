"""Put a build's v1/ tree into the R2 bucket:
python -m happyroads_data.upload --out out"""

import argparse
import hashlib
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

_ROOT = Path(__file__).resolve().parent.parent

# Region files change at most once a build, so a day of caching costs a
# driver nothing. The index and manifests say which build is current, so they
# are cached for an hour: a new month reaches phones the same day.
_REGION_CACHE = 'public, max-age=86400'
_LISTING_CACHE = 'public, max-age=3600'


def headers_for(key):
    headers = {'ContentType': 'application/json; charset=utf-8'}
    if key.endswith('.json.gz'):
        # Stored compressed and labelled as such, so the app's HTTP client
        # undoes it by itself and the bucket holds a fifth of the bytes.
        headers['ContentEncoding'] = 'gzip'
        headers['CacheControl'] = _REGION_CACHE
    else:
        headers['CacheControl'] = _LISTING_CACHE
    return headers


def plan(out):
    """Every file under v1/, in the order it is safe to publish: the region
    files, then the manifests that name them, then the index that names the
    manifests. A phone reading mid-upload never follows a name to a file that
    is not there yet."""
    v1 = Path(out) / 'v1'
    files = [p for p in v1.rglob('*') if p.is_file()]

    def rank(path):
        if path.name == 'index.json' and path.parent == v1:
            return 2
        return 1 if path.name == 'manifest.json' else 0

    files.sort(key=lambda p: (rank(p), p.as_posix()))
    return [(p.relative_to(out).as_posix(), p) for p in files]


def _unchanged(client, bucket, key, body):
    try:
        etag = client.head_object(Bucket=bucket, Key=key)['ETag'].strip('"')
    except (ClientError, KeyError):
        return False
    # A single-part upload's ETag is the MD5 of its bytes, and the build
    # writes the same bytes for the same places, so an unchanged region costs
    # one HEAD and no PUT.
    return etag == hashlib.md5(body).hexdigest()


def upload(out, client, bucket):
    sent = 0
    for key, path in plan(Path(out)):
        body = path.read_bytes()
        if _unchanged(client, bucket, key, body):
            continue
        client.put_object(Bucket=bucket, Key=key, Body=body, **headers_for(key))
        sent += 1
    return sent


def load_env(path):
    values = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            name, value = line.split('=', 1)
            values[name.strip()] = value.strip()
    return values


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--env', default=str(_ROOT / '.env'))
    args = parser.parse_args(argv)

    env = load_env(args.env)
    client = boto3.client(
        's3',
        endpoint_url=env['R2_ENDPOINT'],
        aws_access_key_id=env['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=env['R2_SECRET_ACCESS_KEY'],
        region_name='auto',
    )
    total = len(plan(Path(args.out)))
    sent = upload(Path(args.out), client, env['R2_BUCKET'])
    print(f'{sent} of {total} files sent, {total - sent} unchanged')


if __name__ == '__main__':
    main()
