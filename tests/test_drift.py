"""SELECTORS must say what the app's osm_layers.dart says. The two live in
different repositories, so this runs only when HAPPYROADS_APP points at a
checkout of the app."""

import os
import re
from pathlib import Path

import pytest

from happyroads_data.layers import SELECTORS

APP = os.environ.get('HAPPYROADS_APP')


@pytest.mark.skipif(not APP, reason='HAPPYROADS_APP is not set')
def test_the_selectors_match_the_apps():
    dart = (Path(APP) / 'lib/core/data/osm_layers.dart').read_text(encoding='utf-8')
    body = dart.split('List<String> osmSelectors')[1].split('\n}\n')[0]
    # An arm ends at '],' and a line end. A bare ']' would stop inside the
    # selectors themselves, which are full of brackets.
    arms = re.findall(r'PlaceLayer\.(\w+) => \[(.*?)\],\s*\n', body, re.DOTALL)
    app = {layer: re.findall(r"'([^']*)'", selectors) for layer, selectors in arms}
    assert app == SELECTORS
