from pathlib import Path

import pytest
from shapely.geometry import box

from happyroads_data.config import Alias, CountryConfig, load_country
from happyroads_data.extract import Boundary
from happyroads_data.regions import build_regions, country_boundary

FIXTURES = Path(__file__).parent / 'fixtures'


def _boundary(rel, level, west, **tags):
    return Boundary(rel, {'admin_level': str(level), 'boundary': 'administrative', **tags},
                    box(west, 0, west + 1, 1))


COUNTRY = Boundary(900, {'admin_level': '2', 'boundary': 'administrative',
                         'name': 'Χώρα', 'ISO3166-1': 'XX'}, box(-1, -1, 4, 2))

BOUNDARIES = [
    _boundary(500, 6, 0, name='Δύση', **{'name:en': 'West'}),
    _boundary(501, 6, 1, name='Ανατολή'),
    _boundary(502, 6, 2, name='Νησί', **{'name:en': 'Island', 'name:el': 'Νησί'}),
    COUNTRY,
]


def _config(aliases=(), level=6):
    return CountryConfig('xx', level, list(aliases), 'xx', None, {}, None, {})


def test_a_region_with_no_alias_is_named_by_country_and_relation():
    regions = build_regions(BOUNDARIES, _config())
    assert [r.id for r in regions] == ['xx-500', 'xx-501', 'xx-502']


def test_a_neighbouring_countrys_border_inside_the_extract_is_not_a_region():
    # Geofabrik cuts an extract with a margin, so a county just across the
    # frontier can arrive whole and would otherwise be offered as Greek.
    foreign = _boundary(503, 6, 10, name='Ξένο')
    regions = build_regions([*BOUNDARIES, foreign], _config())
    assert 'xx-503' not in [r.id for r in regions]


def test_its_names_are_osms_own_and_its_neighbours_are_left_to_compute():
    island = build_regions(BOUNDARIES, _config())[2]
    assert island.name == 'Νησί'
    assert island.names == {'en': 'Island', 'el': 'Νησί'}
    assert island.neighbours is None


def test_only_the_countrys_level_becomes_a_region():
    assert build_regions(BOUNDARIES, _config(level=2))[0].id == 'xx-900'


def test_an_alias_keeps_an_old_id_and_its_own_words():
    west = Alias('west', [500], 'Δυτικά', {'en': 'The West'}, ['east'])
    regions = build_regions(BOUNDARIES, _config([west]))
    assert [r.id for r in regions] == ['west', 'xx-501', 'xx-502']
    assert regions[0].names == {'en': 'The West'}
    assert regions[0].neighbours == ['east']


def test_an_alias_of_several_relations_is_one_region_covering_them_all():
    both = Alias('both', [500, 501], 'Και τα δύο', {}, None)
    regions = build_regions(BOUNDARIES, _config([both]))
    assert [r.id for r in regions] == ['both', 'xx-502']
    assert regions[0].geometry.bounds == (0.0, 0.0, 2.0, 1.0)


def test_an_alias_whose_relation_is_missing_stops_the_build():
    # A download id that silently stops existing orphans every device that
    # holds it, so a missing relation has to be loud.
    gone = Alias('gone', [777], 'Χαμένο', {}, None)
    with pytest.raises(ValueError, match='gone.*777'):
        build_regions(BOUNDARIES, _config([gone]))


def test_the_country_is_found_by_its_iso_code():
    assert country_boundary(BOUNDARIES, 'xx').relation_id == 900
    assert country_boundary(BOUNDARIES, 'yy') is None


def test_a_country_reads_its_level_and_its_aliases():
    config = load_country('xx', FIXTURES)
    assert config.level == 6
    assert config.whole_id == 'pretend'
    assert config.whole_names == {'en': 'All of it'}
    assert config.country_name == 'Χώρα (ψευδ.)'
    assert config.aliases[0] == Alias('west', [500], 'Δύση', {'en': 'West'}, [])


def test_a_country_with_no_file_takes_the_default_level_and_its_code_as_whole_id():
    config = load_country('zz', FIXTURES)
    assert (config.level, config.whole_id, config.aliases) == (4, 'zz', [])
