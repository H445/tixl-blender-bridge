"""Seed new editable homes with compact world lanes; never rearrange saved homes."""
import json
import uuid
from pathlib import Path


def layout_home(home: dict, ui: dict, plan: dict, import_id: str) -> None:
    template = json.loads((Path(__file__).resolve().parents[1]
                           / 'templates' / 'home_layout.json').read_text())
    children = {child['Id']: child for child in home['Children']}
    positions = {entry['ChildId']: entry for entry in ui['SymbolChildUis']}
    rows, clip_rows, glass_rows = {}, {}, set()
    y = 0
    for world in plan['worlds']:
        label = world['name'].replace('_', ' ').title()
        members = [child for child in children.values()
                   if child['Name'].startswith(label + ' / ')]
        has_glass = any(' / glass ' in child['Name'].lower() for child in members)
        clip_indices = [index for index, clip in enumerate(plan['clips'])
                        if clip['start'] < world['end'] - 0.0001
                        and clip['end'] > world['start'] + 0.0001]
        rows[label] = y
        if has_glass:
            glass_rows.add(label)
        for offset, index in enumerate(clip_indices):
            # A clip spanning several worlds is placed once, beside its first lane.
            clip_rows.setdefault(index, y + offset * template['clip_spacing'])
        y += max(template['world_spacing'] + (template['pass_spacing'] if has_glass else 0),
                 len(clip_indices) * template['clip_spacing'] + 210)
        y = snap_position((0, y), template['grid'])[1]
    bottom = max((row + (template['pass_spacing'] if label in glass_rows else 0)
                  for label, row in rows.items()), default=0)

    def place(entry, xy, offset=0):
        x, y = snap_position((xy[0], xy[1] + offset), template['grid'])
        entry['Position'] = {'X': x, 'Y': y}

    clip_positions = {str(uuid.uuid5(uuid.NAMESPACE_URL, import_id + f'/clip/{i}')): row
                      for i, row in clip_rows.items()}
    for child_id, entry in positions.items():
        child = children[child_id]
        kind = child['SymbolName'].split('.')[-1]
        prefix = child['Name'].split(' / ')[0]
        if child_id in clip_positions:
            place(entry, template['source_clip'], clip_positions[child_id])
        elif prefix in rows and kind in template['world_roles']:
            offset = template['pass_spacing'] if (
                ' / glass ' in child['Name'].lower()
                or kind == 'Group' and prefix in glass_rows) else 0
            place(entry, template['world_roles'][kind], rows[prefix] + offset)
        elif kind in template['global_roles']:
            place(entry, template['global_roles'][kind])
        elif kind in template['render_roles']:
            role = 'Output target' if child['Name'] == 'Output target' else kind
            place(entry, template['render_roles'][role], bottom)
        else:
            position = entry['Position']
            place(entry, (position['X'], position['Y']))


def snap_position(xy, grid=(140, 35)):
    """Align new home nodes to TiXL's node width and socket line height."""
    return tuple(round(value / step) * step for value, step in zip(xy, grid))
