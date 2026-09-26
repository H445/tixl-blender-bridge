# TiXL bridge workflow

- Before downloading, installing, configuring, or running either application for a new user, read and follow [`.agents/README.md`](.agents/README.md). It is the canonical cross-agent onboarding guide; do not skip the end user's first-run choices, especially the TiXL username/root namespace.
- Before operating or troubleshooting the bridge, read and follow [`.agents/skills/blender-tixl-bridge/SKILL.md`](.agents/skills/blender-tixl-bridge/SKILL.md). It is the capability map and execution playbook for Blender MCP, the TiXL debug protocol, and the bridge's TiXL operators.
- During every agentic install/setup, and after a Blender, Blender MCP, TiXL, or bridge upgrade, rebuild [`.agents/CAPABILITIES.md`](.agents/CAPABILITIES.md) with `.agents/rebuild_capabilities.py`. Supply the live MCP inventory and runtime probes when available; treat any `missing` discovery row as incomplete setup.
- Use Blender MCP for every Blender action, inspection, script execution, scene load, save, and verification.
- Use the TiXL debug bridge for every TiXL launch, project selection, graph inspection, output evaluation, and screenshot. The client is `blender_tixl_bridge/source/tixl_bridge.py`; the normal debug port is 9042.
- Never use Computer Use, screen automation, simulated mouse/keyboard input, or generic UI automation for Blender or TiXL. If Blender MCP or the TiXL debug bridge cannot perform a required action, stop and ask the end user to complete that step manually.
- After changing a loaded `.t3` or `.t3ui` graph structure on disk, TiXL's `reload` command can leave the old graph in memory. Save any editor work, then restart TiXL with `--debug-server 9042` before claiming the new graph is visible.
- Keep generated Blender import data separate from user-edited TiXL home graphs and TimeClips. Check the rendered output as well as graph connections after a sync.
