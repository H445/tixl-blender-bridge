"""Run with: blender --background --python tests/blender_registration_smoke.py"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blender_tixl_bridge

already_enabled = "blender_tixl_bridge" in bpy.context.preferences.addons
if not already_enabled:
    blender_tixl_bridge.register()
assert hasattr(bpy.context.scene, "tixl_bridge_autosync")
assert blender_tixl_bridge.bundled_python().is_file()
if not already_enabled:
    blender_tixl_bridge.unregister()
print("BLENDER_ADDON_REGISTRATION_OK")
