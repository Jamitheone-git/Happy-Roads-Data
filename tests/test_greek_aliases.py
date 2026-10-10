from pathlib import Path

from happyroads_data.config import load_country

ROOT = Path(__file__).resolve().parent.parent


def test_greece_keeps_every_id_the_app_shipped():
    config = load_country('gr', ROOT)
    assert config.level == 6
    assert config.whole_id == 'greece'
    assert len(config.aliases) == 70
    assert config.country_name == 'Ελλάδα'


def test_athens_is_still_the_five_sectors_and_piraeus_as_one():
    athens = next(a for a in load_country('gr', ROOT).aliases if a.id == 'athens')
    assert athens.relations == [2604796, 2607262, 2612469, 2612423, 2616826]


def test_greek_neighbours_are_the_hand_checked_list():
    achaia = next(a for a in load_country('gr', ROOT).aliases if a.id == 'achaia')
    assert achaia.neighbours == ['arcadia', 'corinthia', 'elis']
    assert achaia.names == {'en': 'Achaia'}
