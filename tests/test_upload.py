import gzip
import hashlib

from happyroads_data.upload import credentials, headers_for, load_env, plan, upload


class FakeBucket:
    """Stands in for boto3's S3 client: remembers what was put, in order, and
    answers head_object with the MD5 ETag R2 gives a single-part upload."""

    def __init__(self, existing=None):
        self.objects = dict(existing or {})
        self.puts = []

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)
        return {'ETag': '"' + hashlib.md5(self.objects[Key]['Body']).hexdigest() + '"'}

    def put_object(self, Bucket, Key, Body, **headers):
        self.objects[Key] = {'Body': Body, **headers}
        self.puts.append(Key)


def _tree(tmp_path):
    (tmp_path / 'v1/gr/achaia').mkdir(parents=True)
    (tmp_path / 'v1/gr/achaia/fuel.json.gz').write_bytes(gzip.compress(b'{"fuel":[]}', mtime=0))
    (tmp_path / 'v1/gr/manifest.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'v1/index.json').write_text('{}', encoding='utf-8')
    # The comparison cache sits beside v1/, and is nobody's business but ours.
    (tmp_path / 'overpass_counts.json').write_text('{}', encoding='utf-8')
    return tmp_path


def test_regions_go_first_then_manifests_then_the_index(tmp_path):
    keys = [key for key, _ in plan(_tree(tmp_path))]
    assert keys == ['v1/gr/achaia/fuel.json.gz', 'v1/gr/manifest.json', 'v1/index.json']


def test_a_region_file_is_served_as_gzipped_json():
    headers = headers_for('v1/gr/achaia/fuel.json.gz')
    assert headers['ContentType'] == 'application/json; charset=utf-8'
    assert headers['ContentEncoding'] == 'gzip'
    assert headers['CacheControl'] == 'public, max-age=86400'


def test_a_manifest_is_plain_json_and_cached_briefly():
    headers = headers_for('v1/gr/manifest.json')
    assert 'ContentEncoding' not in headers
    assert headers['CacheControl'] == 'public, max-age=3600'


def test_everything_is_put_with_its_headers(tmp_path):
    bucket = FakeBucket()
    upload(_tree(tmp_path), bucket, 'b')
    assert bucket.puts == ['v1/gr/achaia/fuel.json.gz', 'v1/gr/manifest.json', 'v1/index.json']
    assert bucket.objects['v1/gr/achaia/fuel.json.gz']['ContentEncoding'] == 'gzip'


def test_a_file_already_there_unchanged_is_not_sent_again(tmp_path):
    out = _tree(tmp_path)
    fuel = (out / 'v1/gr/achaia/fuel.json.gz').read_bytes()
    bucket = FakeBucket({'v1/gr/achaia/fuel.json.gz': {'Body': fuel}})
    upload(out, bucket, 'b')
    assert bucket.puts == ['v1/gr/manifest.json', 'v1/index.json']


def test_the_credentials_are_read_from_a_dotenv_file(tmp_path):
    env = tmp_path / '.env'
    env.write_text('R2_BUCKET=happy-roads-data\r\nR2_ENDPOINT=https://x.r2.cloudflarestorage.com\n',
                   encoding='utf-8')
    assert load_env(env) == {'R2_BUCKET': 'happy-roads-data',
                             'R2_ENDPOINT': 'https://x.r2.cloudflarestorage.com'}


def _two_countries(tmp_path):
    out = _tree(tmp_path)
    (out / 'v1/at/tirol').mkdir(parents=True)
    (out / 'v1/at/tirol/fuel.json.gz').write_bytes(gzip.compress(b'{"fuel":[]}', mtime=0))
    (out / 'v1/at/manifest.json').write_text('{}', encoding='utf-8')
    return out


def test_one_country_is_sent_without_the_index_or_any_other_country(tmp_path):
    # A monthly run builds each country in a job of its own, and the index is
    # written once, last, by a job that knows which countries succeeded.
    keys = [key for key, _ in plan(_two_countries(tmp_path), country='gr')]
    assert keys == ['v1/gr/achaia/fuel.json.gz', 'v1/gr/manifest.json']


def test_the_index_alone_is_sent_on_its_own(tmp_path):
    keys = [key for key, _ in plan(_two_countries(tmp_path), index_only=True)]
    assert keys == ['v1/index.json']


def test_with_no_dotenv_the_credentials_come_from_the_environment(tmp_path, monkeypatch):
    # On GitHub Actions they are secrets handed to the step, never a file.
    monkeypatch.setenv('R2_BUCKET', 'from-the-environment')
    assert credentials(tmp_path / 'missing.env')['R2_BUCKET'] == 'from-the-environment'


def test_a_dotenv_wins_when_there_is_one(tmp_path, monkeypatch):
    monkeypatch.setenv('R2_BUCKET', 'from-the-environment')
    env = tmp_path / '.env'
    env.write_text('R2_BUCKET=from-the-file\n', encoding='utf-8')
    assert credentials(env)['R2_BUCKET'] == 'from-the-file'
