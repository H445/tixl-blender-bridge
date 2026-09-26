"""Read-only Blender capability probe. Execute this file through Blender MCP."""

import json

import bpy


def _version(value):
    return ".".join(str(part) for part in value)


addon = bpy.context.preferences.addons.get("blender_tixl_bridge")
module = None
if addon is not None:
    try:
        module = __import__("blender_tixl_bridge")
    except Exception:
        module = None

operator_namespace = getattr(bpy.ops, "tixl_bridge", None)
operators = []
if operator_namespace is not None:
    operators = sorted(name for name in dir(operator_namespace) if not name.startswith("_"))

payload = {
    "blenderVersion": bpy.app.version_string,
    "blenderVersionTuple": list(bpy.app.version),
    "pythonVersion": _version(__import__("sys").version_info[:3]),
    "background": bool(bpy.app.background),
    "addonEnabled": addon is not None,
    "addonVersion": list(getattr(module, "bl_info", {}).get("version", ())) if module else None,
    "bridgeOperators": operators,
    "sceneHasAutosyncProperty": hasattr(bpy.context.scene, "tixl_bridge_autosync"),
    "canExecutePython": True,
    "canReadScene": bpy.context.scene is not None,
    "canOpenAndSaveBlend": hasattr(bpy.ops.wm, "open_mainfile") and hasattr(bpy.ops.wm, "save_mainfile"),
    "canRender": hasattr(bpy.ops.render, "render"),
}

print("BLENDER_TIXL_CAPABILITIES_BEGIN")
print(json.dumps(payload, indent=2, sort_keys=True))
print("BLENDER_TIXL_CAPABILITIES_END")
