"""Check the saved nightclub scene and its exact 120 BPM animation grid.

Run: blender --background examples/humanoid_breakdance.blend --python examples/validate_nightclub.py
"""

import json
from math import hypot

import bpy


scene = bpy.context.scene
assert scene["nightclub_bpm"] == 120
assert scene["nightclub_beat_origin_frame"] == 1
assert scene["nightclub_beat_frames"] == 30
assert scene.render.fps == 60 and scene.frame_end == 7201
worlds = json.loads(scene["tixl_worlds"])
assert len(worlds) == 8
for world in worlds:
    objects = bpy.data.collections[world["collection"]].all_objects
    names = {obj.name for obj in objects}
    assert "Club | raised circular dance floor" in names, world["name"]
    assert "Club | 144 beat-reactive LED tiles" in names, world["name"]
    assert sum(name.startswith("Club | side LED strip") for name in names) == 10
    assert sum(name.startswith("Laser | sweeping ray") for name in names) == 8
    assert sum(name.startswith("Projector | moving floor gobo") for name in names) == 2
    assert sum(name.startswith("Projector | beam edge") for name in names) == 4
    assert sum(obj.type == "LIGHT" for obj in objects) == 6

led = bpy.data.materials["Club / LED phase 1"].node_tree.nodes["Principled BSDF"]
beam = bpy.data.objects["Laser | sweeping ray 01"]
key = bpy.data.objects["Club | warm face key"].data
scene.frame_set(1)
led_on = led.inputs["Emission Strength"].default_value
key_on = key.energy
direction_start = beam.rotation_quaternion.copy()
scene.frame_set(10)
led_off = led.inputs["Emission Strength"].default_value
key_off = key.energy
scene.frame_set(241)
direction_later = beam.rotation_quaternion.copy()
assert led_on > led_off * 4, (led_on, led_off)
assert key_on > key_off, (key_on, key_off)
assert direction_start.rotation_difference(direction_later).angle > 0.1

root_distance = 0.0
for obj in bpy.data.objects:
    if not obj.name.endswith("| motion root"):
        continue
    scene.frame_set(3601)
    root_distance = max(root_distance, hypot(obj.location.x, obj.location.y))
assert root_distance < 3.4, root_distance
scene.frame_set(1)
print(f"NIGHTCLUB_VALIDATED worlds=8 lights=6 beats=240 "
      f"led_on={led_on:.3f} led_off={led_off:.3f} "
      f"max_root_distance={root_distance:.2f}m", flush=True)
