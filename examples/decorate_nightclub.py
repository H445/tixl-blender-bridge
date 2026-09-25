"""Patch the saved humanoid .blend with the beat-locked nightclub set.

Run: blender --background examples/humanoid_breakdance.blend --python examples/decorate_nightclub.py
"""

from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nightclub_set import decorate


scene = bpy.context.scene
decorate(scene)
path = Path(bpy.data.filepath)
if not path.is_file() or path.name != "humanoid_breakdance.blend":
    raise RuntimeError(f"Expected the saved breakdance project, got {path}")
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath and not image.packed_file:
        image.pack()
# This script runs the verified sync explicitly after saving. Avoid a second
# background save handler starting the same export in parallel.
for handler in list(bpy.app.handlers.save_post):
    if getattr(handler, "__module__", "").endswith("tixl_blender_bridge"):
        bpy.app.handlers.save_post.remove(handler)
bpy.ops.wm.save_as_mainfile(filepath=str(path))
print(f"NIGHTCLUB_SAVED {path}", flush=True)
