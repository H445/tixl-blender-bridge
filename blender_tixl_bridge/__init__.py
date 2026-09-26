"""Save-driven Blender to TiXL bridge. The .blend is the authored source."""

bl_info = {
    "name": "Prismal Labs Blender → TiXL Bridge",
    "author": "Prismal Labs",
    "version": (1, 1, 0),
    "blender": (4, 3, 0),
    "location": "Scene Properties > TiXL Bridge",
    "description": "Build TiXL geometry, animation, camera and graph from a saved .blend",
    "category": "Import-Export",
}

import os
import subprocess
from pathlib import Path

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty

ROOT = Path(__file__).resolve().parent
SYNC = ROOT / "source" / "blend_sync.py"


def settings():
    return bpy.context.preferences.addons[__package__].preferences


def bundled_python():
    version = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
    suffix = "python.exe" if os.name == "nt" else "python3"
    candidate = Path(bpy.app.binary_path).parent / version / "python" / "bin" / suffix
    return candidate if candidate.is_file() else None


def queue_sync():
    blend = Path(bpy.data.filepath)
    if not blend.is_file():
        return False, "Save the Blender file first"
    prefs = settings()
    python = bundled_python()
    if python is None:
        return False, "Blender's bundled Python was not found"
    project = Path(bpy.path.abspath(prefs.operator_project))
    editor = Path(bpy.path.abspath(prefs.editor_directory))
    if not next(project.glob("*.csproj"), None) or not (editor / "TiXL.exe").is_file():
        return False, "Set the TiXL operator project and Editor folder in add-on preferences"
    logdir = blend.parent / ".tixl_cache" / blend.stem / "sync_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    output = (logdir / "latest.log").open("a", encoding="utf-8")
    env = dict(os.environ)
    env.update(TIXL_BRIDGE_OPERATOR_PROJECT=str(project), TIXL_BRIDGE_EDITOR=str(editor),
               TIXL_BRIDGE_BLENDER=bpy.app.binary_path,
               TIXL_BRIDGE_MODE=prefs.connection_mode.lower(),
               TIXL_BRIDGE_PORT=str(prefs.debug_port))
    try:
        subprocess.Popen([str(python), str(SYNC), "sync", "--blend", str(blend)],
                         cwd=str(ROOT), env=env, stdout=output, stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
    finally:
        output.close()
    return True, f"TiXL sync queued; log: {logdir / 'latest.log'}"


@persistent
def on_save(_):
    if any(scene.tixl_bridge_autosync for scene in bpy.data.scenes):
        ok, message = queue_sync()
        print(f"TiXL Bridge: {message}")


class TIXLBRIDGE_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    connection_mode: EnumProperty(name="TiXL connection", default="AUTO", items=(
        ("AUTO", "Auto", "Use live reload when a debug bridge is available; otherwise build offline"),
        ("OFFLINE", "Offline", "Build without a debug bridge; works with release builds"),
        ("DEBUG", "Debug bridge", "Use live reload; launch TiXL with its debug server when needed")))
    debug_port: IntProperty(name="Debug port", default=9042, min=1, max=65535)
    operator_project: StringProperty(name="TiXL operator project", subtype="DIR_PATH",
        description="TiXL project folder containing a .csproj and Symbols directory")
    editor_directory: StringProperty(name="TiXL Editor folder", subtype="DIR_PATH",
        description="Built TiXL Editor folder containing TiXL.exe")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "operator_project")
        layout.prop(self, "editor_directory")
        layout.prop(self, "connection_mode")
        if self.connection_mode != "OFFLINE":
            layout.prop(self, "debug_port")
        layout.label(text="Set these once; each .blend gets its own generated TiXL project.")


class TIXLBRIDGE_OT_sync_now(bpy.types.Operator):
    bl_idname = "tixl_bridge.sync_saved_blend"
    bl_label = "Sync saved .blend to TiXL"
    bl_description = "Queue a background rebuild of the saved Blender project"

    def execute(self, context):
        ok, message = queue_sync()
        self.report({"INFO" if ok else "ERROR"}, message)
        return {"FINISHED"} if ok else {"CANCELLED"}


class TIXLBRIDGE_PT_scene(bpy.types.Panel):
    bl_label = "TiXL Bridge"
    bl_idname = "TIXLBRIDGE_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        self.layout.prop(context.scene, "tixl_bridge_autosync", text="Sync after save")
        self.layout.operator("tixl_bridge.sync_saved_blend")
        self.layout.label(text="The .blend is the source; exports are generated.")


CLASSES = (TIXLBRIDGE_preferences, TIXLBRIDGE_OT_sync_now, TIXLBRIDGE_PT_scene)


def register():
    bpy.types.Scene.tixl_bridge_autosync = BoolProperty(name="Sync after save", default=False)
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    if on_save not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(on_save)


def unregister():
    if on_save in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(on_save)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.tixl_bridge_autosync
