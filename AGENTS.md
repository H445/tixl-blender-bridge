# Repository workflow

When changing any file in `tixl_blender_bridge/`, rebuild the add-on ZIP with `python build_addon_zip.py`, then run `install_blender_addon.py` through the local Blender executable before finishing. The installer copies the current checkout into Blender's user add-ons directory, enables the add-on, preserves existing preferences unless explicitly passed new values, and verifies copied file hashes. Verify it persists in a second Blender background process. If Blender is already running interactively, tell the user to restart Blender to load the updated code there.

Locate the local Blender executable for the current machine rather than committing its path. Do not commit personal TiXL paths or Blender user preferences. Keep the installable ZIP current in the same commit as add-on source changes.
