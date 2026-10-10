"""Borders into the regions a driver downloads, each with an id that must not
change from one month's build to the next."""

from dataclasses import dataclass

from shapely.ops import unary_union

# The app speaks two languages. A region's name in either one comes from OSM's
# name:<code> when an alias does not give it.
LANGUAGES = ('en', 'el')


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    names: dict
    geometry: object
    neighbours: list | None


def build_regions(boundaries, config):
    by_relation = {b.relation_id: b for b in boundaries}
    country = country_boundary(boundaries, config.id)
    taken = set()
    regions = []

    for alias in config.aliases:
        missing = [r for r in alias.relations if r not in by_relation]
        if missing:
            raise ValueError(f'alias {alias.id}: relation {missing[0]} is not in the extract')
        taken.update(alias.relations)
        regions.append(Region(
            alias.id, alias.name, alias.names,
            unary_union([by_relation[r].geometry for r in alias.relations]),
            alias.neighbours))

    for boundary in boundaries:
        if boundary.relation_id in taken:
            continue
        if boundary.tags.get('admin_level') != str(config.level):
            continue
        # Geofabrik cuts an extract with a margin, so a neighbouring country's
        # county can arrive whole. One whose inside is not inside this country
        # belongs to the neighbour. An alias is exempt: it was named on purpose.
        if (country is not None and boundary.relation_id != country.relation_id
                and not country.geometry.contains(boundary.geometry.representative_point())):
            continue
        region_id = f'{config.id}-{boundary.relation_id}'
        regions.append(Region(
            region_id,
            boundary.tags.get('name', region_id),
            {lang: boundary.tags[f'name:{lang}'] for lang in LANGUAGES
             if f'name:{lang}' in boundary.tags},
            boundary.geometry,
            None))

    return sorted(regions, key=lambda r: r.id)


def country_boundary(boundaries, cc):
    code = cc.upper()
    for boundary in boundaries:
        if boundary.tags.get('admin_level') == '2' and code in (
                boundary.tags.get('ISO3166-1'), boundary.tags.get('ISO3166-1:alpha2')):
            return boundary
    return None
