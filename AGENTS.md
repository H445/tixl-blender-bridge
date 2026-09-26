# TiXL bridge workflow

- Use the TiXL debug bridge first for launch, project selection, graph inspection, output evaluation, and screenshots. The client is `blender_tixl_bridge/source/tixl_bridge.py`; the normal debug port is 9042.
- Use computer control only when the debug bridge cannot perform the needed check or action.
- After changing a loaded `.t3` or `.t3ui` graph structure on disk, TiXL's `reload` command can leave the old graph in memory. Save any editor work, then restart TiXL with `--debug-server 9042` before claiming the new graph is visible.
- Keep generated Blender import data separate from user-edited TiXL home graphs and TimeClips. Check the rendered output as well as graph connections after a sync.
