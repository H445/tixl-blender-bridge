"""Run with Blender --background examples/BlendShapeExample.blend --python this file."""
from collections import Counter
import json

import bpy
from mathutils import Vector

scene = bpy.context.scene
names = ('Cube', 'Sphere', 'Prism', 'Cylinder')
assert scene.render.fps == 60 and scene.frame_end - scene.frame_start == 960
assert scene['bpm'] == 120 and len(json.loads(scene['tixl_worlds'])) == 4
assert scene['tixl_project_name'] == 'BlendShapeExample'
for index, name in enumerate(names):
    obj = bpy.data.objects[name]
    assert obj.location.length < 1e-8
    basis, target = obj.data.shape_keys.key_blocks
    following = bpy.data.objects[names[(index + 1) % 4]].data.shape_keys.key_blocks[0]
    assert len(basis.data) == len(target.data) == len(following.data)
    assert all((a.co - b.co).length < 1e-6 for a, b in zip(target.data, following.data))
    edges = Counter()
    volume = 0.0
    centroid = Vector()
    for face in obj.data.polygons:
        ids = list(face.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges[tuple(sorted((a, b)))] += 1
        a = basis.data[ids[0]].co
        for i in range(1, len(ids) - 1):
            b, c = basis.data[ids[i]].co, basis.data[ids[i + 1]].co
            v = a.dot(b.cross(c)) / 6
            volume += v
            centroid += v * (a + b + c) / 4
    assert set(edges.values()) == {2}, name
    assert volume > 0 and (centroid / volume).length < 1e-5, (name, centroid / volume)
    for offset, expected in ((0, 0), (120, 0), (180, 0.5), (240, 1)):
        scene.frame_set(1 + index * 240 + offset)
        assert abs(target.value - expected) < 1e-5, (name, offset, target.value)
for frame in (1, 181, 241, 421, 481, 661, 721, 901, 961):
    scene.frame_set(frame)
    assert sum(not bpy.data.objects[name].hide_render for name in names) == 1, frame
scene.frame_set(1)
print('BLEND_SHAPE_EXAMPLE_VALID: closed centered meshes, continuous boundaries, beat-aligned morphs')
