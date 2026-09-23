"""Run with: blender --background --python tests/blender_registration_smoke.py"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tixl_blender_bridge

tixl_blender_bridge.register()
assert hasattr(bpy.context.scene, "tixl_bridge_autosync")
assert tixl_blender_bridge.bundled_python().is_file()
tixl_blender_bridge.unregister()
print("BLENDER_ADDON_REGISTRATION_OK")
