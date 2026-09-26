"""Build the release example: blender --background --python examples/build_shape_cycle.py."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "Shape Cycle - 120 BPM"
scene.render.fps = 60
scene.frame_start, scene.frame_end = 1, 961
scene.render.engine = ('BLENDER_EEVEE_NEXT' if bpy.app.version < (5, 0, 0)
                       else 'BLENDER_EEVEE')
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.render.resolution_percentage = 100
scene.world = bpy.data.worlds.new('World')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.025, 0.025, 0.025, 1)
scene['bpm'] = 120
scene['description'] = 'Four worlds; eight beats each: hold four, morph four. Loop 0-16 seconds.'

# Rings align with both square and triangular corners, and with cap edges.
# This avoids triangles crossing a sharp edge and creating a jagged silhouette.
segments = 96
rings = [(r, -1) for r in (0.25, 0.5, 0.75)]
rings += [(1, -1 + i / 8) for i in range(17)]
rings += [(r, 1) for r in (0.75, 0.5, 0.25)]
coords = [Vector((0, 0, -1))]
for radius, z in rings:
    coords.extend(Vector((radius * math.cos(i * math.tau / segments),
                          radius * math.sin(i * math.tau / segments), z))
                  for i in range(segments))
coords.append(Vector((0, 0, 1)))
faces = [(0, 1 + (i + 1) % segments, 1 + i) for i in range(segments)]
for ring in range(len(rings) - 1):
    a, b = 1 + ring * segments, 1 + (ring + 1) * segments
    faces.extend((a + i, a + (i + 1) % segments,
                  b + (i + 1) % segments, b + i) for i in range(segments))
top = len(coords) - 1
last = 1 + (len(rings) - 1) * segments
faces.extend((last + i, last + (i + 1) % segments, top)
             for i in range(segments))

def target(p, kind):
    if kind == 'Cube':
        radius = math.hypot(p.x, p.y)
        scale = radius / max(abs(p.x), abs(p.y)) if radius else 1
        return Vector((p.x * scale, p.y * scale, p.z))
    if kind == 'Sphere':
        return p.normalized()
    radial = math.hypot(p.x, p.y)
    if kind == 'Cylinder':
        return p.copy()
    # Equilateral triangular prism, circumradius 1.4, centered at the origin.
    planes = [p.x * math.cos(a) + p.y * math.sin(a)
              for a in (math.pi, math.pi / 3, -math.pi / 3)]
    scale = 0.7 * radial / max(planes) if radial else 1
    return Vector((p.x * scale, p.y * scale, p.z))

targets = {name: [target(p, name) for p in coords]
           for name in ('Cube', 'Sphere', 'Prism', 'Cylinder')}
material = bpy.data.materials.new('Neutral blue')
material.diffuse_color = (0.12, 0.42, 0.8, 1)
material.use_nodes = True
bsdf = material.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = material.diffuse_color
bsdf.inputs['Roughness'].default_value = 0.35

bpy.ops.object.camera_add(location=(4.5, -6.5, 3.5))
camera = bpy.context.object
camera.name = 'Camera'
camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'PERSP'
camera.data.lens = 50
scene.camera = camera
worlds = []
names = list(targets)
for index, name in enumerate(names):
    following = names[(index + 1) % 4]
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(targets[name], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.shape_key_add(name='Basis')
    key = obj.shape_key_add(name='To ' + following)
    for v, co in zip(key.data, targets[following]):
        v.co = co
    start = 1 + index * 240
    for frame, value in ((1, 0), (start + 120, 0), (start + 240, 1), (961, 1)):
        key.value = value
        key.keyframe_insert('value', frame=frame)
    # Each collection supplies its own light to the exported TiXL world.
    data = bpy.data.lights.new(name + ' Key', 'POINT')
    data.energy = 1200
    light = bpy.data.objects.new(data.name, data)
    light.location = (3, -4, 5)
    collection.objects.link(light)
    for frame, hidden in ((1, index != 0), (start, False),
                          (start + 240, index != 3)):
        for item in (obj, light):
            item.hide_render = hidden
            item.keyframe_insert('hide_render', frame=frame)
    worlds.append(dict(name=name.lower(), collection=name,
                       start_seconds=index * 4, end_seconds=(index + 1) * 4))
    marker = scene.timeline_markers.new(name + ' to ' + following, frame=start)
    marker.camera = camera
scene['tixl_worlds'] = json.dumps(worlds)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'shape_cycle.blend'))
print('SHAPE_CYCLE_BUILT', len(coords), 'vertices per world')
