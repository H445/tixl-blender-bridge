"""Rebuild the agent-facing capability snapshot from current bridge and app evidence."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any


AGENTS_DIR = Path(__file__).resolve().parent
REPOSITORY = AGENTS_DIR.parent
DEFAULT_OUTPUT = AGENTS_DIR / "CAPABILITIES.md"
DEBUG_SERVER_RELATIVE = Path("Editor/App/DebugProtocol/DebugServer.cs")

KNOWN_TIXL_METHODS = {
    "ping": ("Inspection", "Confirm the main-thread request queue responds."),
    "setAgentState": ("Coordination", "Publish busy/ready state and a note in the editor."),
    "getVersion": ("Inspection", "Read protocol and editor versions."),
    "shutdown": ("Lifecycle", "Exit TiXL; unsaved changes are discarded."),
    "getStructureVersion": ("Inspection", "Read the symbol-structure version counter."),
    "getLogTail": ("Diagnostics", "Read buffered log entries incrementally."),
    "getContext": ("Inspection", "Read project, composition, selection, output, time, and playback context."),
    "getGraphState": ("Inspection", "Read graph children, values, positions, connections, and unresolved structure."),
    "getMetrics": ("Diagnostics", "Read FPS, memory, render statistics, and GPU memory."),
    "screenshot": ("Evidence", "Capture output texture or editor-rendered UI."),
    "screenshotWindow": ("Evidence", "Capture the editor client area or graph region."),
    "openProject": ("Navigation", "Open a project by name or symbol ID and optionally pin its output."),
    "select": ("Navigation", "Select graph children by stable IDs."),
    "getGraphView": ("Inspection", "Read graph camera and visible bounds."),
    "setGraphView": ("Navigation", "Set graph camera, zoom, scroll, or fitted area."),
    "focusGraphView": ("Navigation", "Frame selected, specified, missing, or all operators."),
    "setInput": ("Mutation", "Set a typed child input with undo support."),
    "getOutput": ("Evaluation", "Evaluate scalar, vector, string, bool, or mesh output data."),
    "pumpFrames": ("Evaluation", "Advance deterministic editor frames."),
    "newProject": ("Creation", "Create and compile a shared-resource project."),
    "addOp": ("Mutation", "Add an operator by symbol name or ID."),
    "connect": ("Mutation", "Create a type-checked, cycle-checked connection."),
    "deleteOp": ("Mutation", "Delete an operator with undo support."),
    "pin": ("Evaluation", "Pin a child in the output window."),
    "setBypass": ("Mutation", "Bypass or re-enable a compatible operator."),
    "outputSetup": ("Output", "Drive output-setup state through the protocol."),
    "resetView": ("Output", "Reset the output view."),
    "reload": ("Build", "Recompile an editable project."),
    "stallMainThread": ("Test only", "Inject a main-thread stall; never use in normal operation."),
    "undo": ("Mutation", "Undo the latest editor command."),
    "redo": ("Mutation", "Redo the latest undone command."),
    "setTime": ("Evaluation", "Set timeline time in seconds or bars."),
    "setPlayback": ("Evaluation", "Pause, play, or change playback speed."),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tixl-source", type=Path, help="TiXL source root matching the installed editor")
    parser.add_argument("--tixl-port", type=int, help="Running TiXL debug-server port")
    parser.add_argument("--blender-probe", type=Path, help="JSON captured from probes/blender_runtime_probe.py")
    parser.add_argument("--blender-mcp-tools", type=Path, help="JSON inventory of advertised Blender MCP tools")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Fail when the output differs from current evidence")
    return parser.parse_args()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_json(path: Path | None) -> Any:
    if path is None:
        return None
    text = path.read_text(encoding="utf-8")
    begin = "BLENDER_TIXL_CAPABILITIES_BEGIN"
    end = "BLENDER_TIXL_CAPABILITIES_END"
    if begin in text and end in text:
        text = text.split(begin, 1)[1].split(end, 1)[0]
    return json.loads(text)


def normalize_mcp_tools(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        raw = raw.get("tools", raw.get("capabilities", []))
    result = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, str):
            result.append({"name": item, "description": ""})
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("tool") or "").strip()
            if name:
                description = " ".join(str(item.get("description") or "").split())
                result.append({"name": name, "description": description[:500]})
    return sorted(result, key=lambda item: item["name"].lower())


def parse_bridge_metadata() -> dict[str, Any]:
    source = REPOSITORY / "blender_tixl_bridge" / "__init__.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    bl_info: dict[str, Any] = {}
    operators: list[str] = []
    properties: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "bl_info" for target in node.targets):
                bl_info = ast.literal_eval(node.value)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "bl_idname":
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        continue
                    if isinstance(value, str) and value.startswith("tixl_bridge."):
                        operators.append(value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            declaration = node.value if isinstance(node.value, ast.Call) else node.annotation
            if not isinstance(declaration, ast.Call):
                continue
            function = declaration.func
            name = function.id if isinstance(function, ast.Name) else ""
            if name.endswith("Property"):
                properties.append(node.target.id)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            function = node.value.func
            name = function.id if isinstance(function, ast.Name) else ""
            if not name.endswith("Property"):
                continue
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    properties.append(target.attr)
    return {
        "source": source,
        "name": bl_info.get("name", ""),
        "version": ".".join(str(v) for v in bl_info.get("version", ())),
        "minimumBlender": ".".join(str(v) for v in bl_info.get("blender", ())),
        "operators": sorted(set(operators)),
        "preferences": sorted(set(properties)),
    }


def parse_bridge_operators() -> list[dict[str, str]]:
    result = []
    folder = REPOSITORY / "blender_tixl_bridge" / "operators"
    for path in sorted(folder.glob("Blender*.t3ui")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        result.append({"name": path.stem, "description": " ".join(data.get("Description", "").split())})
    return result


def infer_tixl_source(explicit: Path | None) -> Path | None:
    candidates = [explicit]
    env = os.environ.get("TIXL_SOURCE")
    if env:
        candidates.append(Path(env))
    candidates.append(REPOSITORY.parent.parent / "tixl")
    for candidate in candidates:
        if candidate and (candidate / DEBUG_SERVER_RELATIVE).is_file():
            return candidate.resolve()
    return None


def parse_tixl_methods(source_root: Path | None) -> tuple[dict[str, int], Path | None]:
    if source_root is None:
        return {}, None
    path = source_root / DEBUG_SERVER_RELATIVE
    text = path.read_text(encoding="utf-8-sig")
    methods = {
        match.group(1): text.count("\n", 0, match.start()) + 1
        for match in re.finditer(r'^[ \t]*case[ \t]+"([^"]+)"[ \t]*:', text, flags=re.MULTILINE)
    }
    return methods, path


def live_call(port: int, method: str, timeout: float = 4.0) -> dict[str, Any]:
    request = {"id": str(time.time_ns()), "method": method}
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall((json.dumps(request) + "\n").encode("utf-8"))
        line = connection.makefile("r", encoding="utf-8").readline()
    if not line:
        raise ConnectionError("TiXL debug server closed without a response")
    return json.loads(line)


def probe_tixl(port: int | None) -> dict[str, Any] | None:
    if port is None:
        return None
    result: dict[str, Any] = {"port": port}
    try:
        version = live_call(port, "getVersion")
        result["version"] = version.get("result") if version.get("ok") else version.get("error")
        capabilities = live_call(port, "getCapabilities")
        if capabilities.get("ok"):
            result["capabilities"] = capabilities.get("result")
        else:
            result["capabilityDiscovery"] = "not supported by this protocol version"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def escape_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render(args: argparse.Namespace) -> str:
    bridge = parse_bridge_metadata()
    bridge_ops = parse_bridge_operators()
    tixl_source = infer_tixl_source(args.tixl_source)
    tixl_methods, debug_server = parse_tixl_methods(tixl_source)
    blender_probe = load_json(args.blender_probe)
    mcp_tools = normalize_mcp_tools(load_json(args.blender_mcp_tools))
    live_tixl = probe_tixl(args.tixl_port)

    live_methods: dict[str, dict[str, Any]] = {}
    if live_tixl and isinstance(live_tixl.get("capabilities"), dict):
        raw_methods = live_tixl["capabilities"].get("methods", [])
        for item in raw_methods:
            if isinstance(item, dict) and item.get("name"):
                live_methods[str(item["name"])] = item
            elif isinstance(item, str):
                live_methods[item] = {}
    methods = sorted(set(tixl_methods) | set(live_methods))

    lines = [
        "# Discovered Blender–TiXL capabilities",
        "",
        "> Generated by `.agents/rebuild_capabilities.py`. Do not hand-edit. Rebuild during agentic setup and after component upgrades.",
        "",
        "## Discovery coverage",
        "",
        "| Source | Status | Evidence |",
        "| --- | --- | --- |",
        f"| Bridge checkout | complete | add-on {escape_cell(bridge['version'])}; source SHA-256 `{digest(bridge['source'])}` |",
        f"| Blender runtime via MCP | {'complete' if blender_probe else 'missing'} | {escape_cell((blender_probe or {}).get('blenderVersion', 'Run the MCP probe'))} |",
        f"| Blender MCP advertised tools | {'complete' if mcp_tools else 'missing'} | {len(mcp_tools)} tools inventoried |",
        f"| TiXL source | {'complete' if debug_server else 'missing'} | " + (f"matching `{DEBUG_SERVER_RELATIVE.as_posix()}`; SHA-256 `{digest(debug_server)}` |" if debug_server else "Pass --tixl-source |"),
        f"| Live TiXL debug server | {'complete' if live_tixl and not live_tixl.get('error') else 'missing'} | {escape_cell(json.dumps(live_tixl, sort_keys=True) if live_tixl else 'Pass --tixl-port')} |",
        "",
        "Any `missing` row means setup has not fully inventoried the current environment. Do not assume the checked-in baseline covers an upgraded component.",
        "",
        "## Blender bridge runtime",
        "",
        f"- Add-on: **{bridge['name']} {bridge['version']}**",
        f"- Minimum Blender declared by add-on: **{bridge['minimumBlender']}**",
        f"- Registered bridge operators: {', '.join(f'`{name}`' for name in bridge['operators']) or 'none discovered'}",
        f"- Add-on properties discovered from source: {', '.join(f'`{name}`' for name in bridge['preferences']) or 'none discovered'}",
    ]
    if blender_probe:
        lines.extend(["", "Runtime probe:", "", "```json", json.dumps(blender_probe, indent=2, sort_keys=True), "```"])

    lines.extend(["", "## Blender MCP tools advertised during setup", ""])
    if mcp_tools:
        lines.extend(["| Tool | Advertised capability |", "| --- | --- |"])
        lines.extend(f"| `{escape_cell(tool['name'])}` | {escape_cell(tool['description'])} |" for tool in mcp_tools)
    else:
        lines.append("No MCP inventory was supplied. Rebuild with `--blender-mcp-tools` before claiming MCP-specific proficiency.")

    lines.extend(["", "## TiXL debug-protocol methods", ""])
    if methods:
        lines.extend(["| Method | Category | Capability | Evidence |", "| --- | --- | --- | --- |"])
        for method in methods:
            advertised = live_methods.get(method, {})
            fallback = advertised.get("description") or "Inspect the matching server handler before use."
            category, description = KNOWN_TIXL_METHODS.get(method, ("**Unclassified**", fallback))
            evidence = []
            if method in tixl_methods:
                evidence.append(f"`DebugServer.cs:{tixl_methods[method]}`")
            if method in live_methods:
                evidence.append("live server")
            lines.append(f"| `{escape_cell(method)}` | {category} | {escape_cell(description)} | {', '.join(evidence)} |")
    else:
        lines.append("No TiXL method inventory was available. Pass the matching TiXL source root or use a server that advertises capabilities.")

    lines.extend(["", "## Reusable TiXL bridge operators", "", "| Operator | Contract from current `.t3ui` |", "| --- | --- |"])
    lines.extend(f"| `{escape_cell(op['name'])}` | {escape_cell(op['description'])} |" for op in bridge_ops)

    unclassified = sorted(method for method in methods if method not in KNOWN_TIXL_METHODS)
    lines.extend(["", "## Review result", ""])
    if unclassified:
        lines.append("Unclassified TiXL methods require handler review before use: " + ", ".join(f"`{name}`" for name in unclassified) + ".")
    else:
        lines.append("No unclassified TiXL methods were discovered.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    content = render(args)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            print(f"Capability snapshot is stale: {output}", file=sys.stderr)
            return 1
        print(f"Capability snapshot is current: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8", newline="\n")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
