"""Render a quick Blender nightclub check without changing the saved scene.

Run: blender --background examples/humanoid_breakdance.blend \
    --python examples/render_nightclub_preview.py -- 1 examples/nightclub-opening.png
"""

import sys
from pathlib import Path

import bpy


args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) != 2:
    raise ValueError("Expected frame number and output PNG path after --")
frame = int(args[0])
output = Path(args[1]).resolve()
output.parent.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.frame_set(frame)
scene.render.resolution_percentage = 75
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(output)
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
bpy.ops.render.render(write_still=True)
print(f"NIGHTCLUB_PREVIEW {frame} {output}", flush=True)
