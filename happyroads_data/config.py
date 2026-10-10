"""Per-country settings: the level a country is divided at, and the aliases
that keep ids a device already holds."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Alias:
    id: str
    relations: list
    name: str
    names: dict
    neighbours: list | None


@dataclass(frozen=True)
class CountryConfig:
    id: str
    level: int
    aliases: list
    whole_id: str
    whole_name: str | None
    whole_names: dict
    country_name: str | None
    country_names: dict = field(default_factory=dict)


def load_country(cc, root):
    root = Path(root)
    levels = tomllib.loads((root / 'levels.toml').read_text(encoding='utf-8'))
    level = levels.get('levels', {}).get(cc, levels['default'])

    path = root / 'aliases' / f'{cc}.toml'
    data = tomllib.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    whole = data.get('whole', {})
    country = data.get('country', {})

    return CountryConfig(
        id=cc,
        level=level,
        aliases=[Alias(a['id'], a['relations'], a['name'], a.get('names', {}),
                       a.get('neighbours'))
                 for a in data.get('region', [])],
        whole_id=whole.get('id', cc),
        whole_name=whole.get('name'),
        whole_names=whole.get('names', {}),
        country_name=country.get('name'),
        country_names=country.get('names', {}),
    )
