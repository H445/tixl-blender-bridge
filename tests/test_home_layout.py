"""Layout checks for varying world/pass counts and preservation of editor work."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'blender_tixl_bridge' / 'source'))
from blend_sync_graph import generate
from blend_sync_project import create_scaffold, populate
from blend_sync_layout import layout_home


class HomeLayoutTest(unittest.TestCase):
    def test_dynamic_lanes_and_saved_layout(self):
        for count, glass, clips_per_world in ((1, False, 1), (4, False, 1), (7, True, 6)):
            with self.subTest(worlds=count, glass=glass), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                blend = root / 'ArbitraryScene.blend'
                blend.write_bytes(b'scene')
                cache = root / 'cache'
                cache.mkdir()
                (cache / 'camera_timeline.json').write_text(json.dumps({
                    'shots': [{'id': i + 1, 'start': i * 4 / clips_per_world,
                               'label': f'Shot {i}'}
                              for i in range(count * clips_per_world)], 'passages': []}))
                files = generate(blend, cache, {'fps': 60, 'worlds': [
                    {'world': f'world_{i}', 'active_clip': [i * 240 + 1, (i + 1) * 240 + 1],
                     'opaque_count': 1, 'glass_count': int(glass)} for i in range(count)]})
                template = root / 'template'
                template.mkdir()
                (template / 'Template.csproj').write_text(
                    '<Project><RootNamespace>X</RootNamespace><HomeGuid>X</HomeGuid>'
                    '<PackageId>X</PackageId></Project>')
                project = root / 'project'
                create_scaffold(project, 'LayoutProject', template, blend)
                populate(project, files, root / 'backups', root, build=False)
                path = project / 'Symbols' / 'LayoutProject.t3'
                ui_path = path.with_suffix('.t3ui')
                home, ui = json.loads(path.read_text()), json.loads(ui_path.read_text())
                positions = {entry['ChildId']: entry['Position'] for entry in ui['SymbolChildUis']}
                named = {child['Name']: positions[child['Id']] for child in home['Children']}
                for i in range(count):
                    prefix = f'World {i} / '
                    load = named[prefix + 'opaque load']
                    motion = named[prefix + 'opaque motion']
                    select = named[prefix + 'opaque select mesh']
                    self.assertEqual(motion['X'], select['X'])
                    self.assertGreater(select['Y'], motion['Y'])
                    self.assertGreater(named[prefix + 'opaque replace mesh']['X'], select['X'])
                    self.assertEqual(load['Y'], motion['Y'])
                    if i:
                        self.assertGreaterEqual(load['Y'] - named[f'World {i-1} / opaque load']['Y'],
                                                420 + (180 if glass else 0))
                    if glass:
                        self.assertEqual(named[prefix + 'glass load']['Y'] - load['Y'], 180)
                original = copy.deepcopy(home)
                layout_home(home, ui, json.loads(files[3].read_text()),
                            json.loads(files[0].read_text())['Id'])
                self.assertEqual(home, original)  # Layout must never rewrite graph connections or values.
                ui['SymbolChildUis'][0]['Position'] = {'X': -777, 'Y': 1234}
                ui_path.write_text(json.dumps(ui))
                saved = ui_path.read_bytes()
                populate(project, files, root / 'backups', root, build=False)
                self.assertEqual(ui_path.read_bytes(), saved)


if __name__ == '__main__':
    unittest.main()
