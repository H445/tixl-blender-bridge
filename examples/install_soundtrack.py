"""Idempotently attach the demo score to a saved TiXL bridge project.

Run while TiXL is closed, then launch TiXL with the debug bridge. This edits
only the user-owned home graph, leaving generated Blender import symbols alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path
from xml.etree import ElementTree


HERE = Path(__file__).resolve().parent
WAV = HERE / "audio" / "breakdance_nightclub_120bpm.wav"
ZERO = "00000000-0000-0000-0000-000000000000"

AUDIO_CLIP = "f0008b50-091d-4e9f-91eb-baa212acfa20"
AUDIO_REF = "4c9e7a20-3f81-4d5a-b6e2-1a2b3c4d5e6f"
AUDIO_TIME = "5fb7a174-9ab2-4688-89a0-7fbcbf831dcf"
AUDIO_PATH = "625951af-5f99-4171-b5b0-c97413121f56"
AUDIO_AUTOPLAY = "260b61ae-7605-4f06-a3fb-793ae5a23646"
AUDIO_DISPLAY = "8f2e6b10-4c5d-4e8f-9a1b-2c3d4e5f6a70"
AUDIO_STYLE = "9a3f7c20-5d6e-4f9a-8b2c-3d4e5f6a7b80"

BUS = "b7e0d240-1e42-4c8a-9f31-0ab1cd2e0100"
BUS_INPUT = "b7e0d240-0002-4c8a-9f31-0ab1cd2e0100"
BUS_RESULT = "b7e0d240-0001-4c8a-9f31-0ab1cd2e0100"

EXECUTE = "936e4324-bea2-463a-b196-6064a2d8a6b2"
EXECUTE_INPUT = "5d73ebe6-9aa0-471a-ae6b-3f5bfd5a0f9c"
EXECUTE_OUTPUT = "e81c99ce-fcee-4e7c-a1c7-0aa3b352b7e1"

RENDER_COMMAND = "4da253b7-4953-439a-b03f-1d515a78bddf"


def read_t3(path: Path) -> dict:
    text = re.sub(r'("[0-9a-fA-F-]{36}")/\*.*?\*/', r"\1", path.read_text(encoding="utf-8"))
    return json.loads(text)


def write_t3(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def edge(src: str, src_slot: str, dst: str, dst_slot: str) -> dict:
    return {"SourceParentOrChildId": src, "SourceSlotId": src_slot,
            "TargetParentOrChildId": dst, "TargetSlotId": dst_slot}


def child_id(home_id: str, suffix: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, home_id + "/soundtrack/" + suffix))


def file_hash(path: Path) -> bytes:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.digest()


def install(project: Path) -> None:
    if not WAV.is_file():
        raise FileNotFoundError(f"Render the score first: {WAV}")
    symbol = project / "Symbols" / "TixlBlenderBridge.t3"
    ui_file = symbol.with_suffix(".t3ui")
    home = read_t3(symbol)
    ui = read_t3(ui_file)
    if home["Id"] != ui["Id"] or home["ProjectSettings"]["Playback"]["Bpm"] != 120:
        raise ValueError("Home symbol/UI mismatch or project is not at 120 BPM")

    clip = child_id(home["Id"], "clip")
    bus = child_id(home["Id"], "bus")
    execute = child_id(home["Id"], "execute")
    children = {item["Id"]: item for item in home["Children"]}
    existing = [id_ for id_ in (clip, bus, execute) if id_ in children]
    if existing:
        if len(existing) != 3:
            raise ValueError("Partial soundtrack graph exists; inspect before retrying")
        print("Soundtrack graph already installed; preserving user edits")
    else:
        # The final render target is guaranteed to pull this command input for
        # both the live view and exported frames.
        final_targets = [c for c in home["Children"] if c.get("Name") == "Output target"]
        if len(final_targets) != 1:
            raise ValueError("Expected one Output target")
        target = final_targets[0]["Id"]
        render_edges = [e for e in home["Connections"]
                        if e["TargetParentOrChildId"] == target and e["TargetSlotId"] == RENDER_COMMAND]
        if len(render_edges) != 1:
            raise ValueError("Expected one picture command feeding Output target")
        picture = render_edges[0]
        home["Connections"].remove(picture)

        namespace = ElementTree.parse(project / f"{project.name}.csproj").findtext(
            ".//{*}RootNamespace") or project.name
        asset_address = f"{namespace}:audio/{WAV.name}"
        home["Children"].extend([
            {"Id": clip, "SymbolId": AUDIO_CLIP, "SymbolName": "Lib.io.audio.AudioClip",
             "Name": "Soundtrack / 120 BPM / ten movements",
             "InputValues": [
                 {"Id": AUDIO_PATH, "Type": "System.String", "Value": asset_address},
                 {"Id": AUDIO_AUTOPLAY, "Type": "System.Boolean", "Value": False},
                 {"Id": AUDIO_DISPLAY, "Type": "System.Int32", "Value": 1},
                 {"Id": AUDIO_STYLE, "Type": "System.Int32", "Value": 1},
             ],
             "Outputs": [{"Id": AUDIO_TIME, "OutputData": {
                 "Type": "T3.Core.Animation.TimeClip", "TimeClip": {
                     "TimeRange": {"Start": 0.0, "End": 60.0},
                     "SourceRange": {"Start": 0.0, "End": 120.0},
                     "LayerIndex": 1, "SourceUnit": "Seconds"}}}]},
            {"Id": bus, "SymbolId": BUS, "SymbolName": "Lib.io.audio.AudioBus",
             "Name": "Soundtrack bus / mix here", "InputValues": [], "Outputs": []},
            {"Id": execute, "SymbolId": EXECUTE, "SymbolName": "Lib.flow.Execute",
             "Name": "Execute / picture + soundtrack", "InputValues": [], "Outputs": []},
        ])
        home["Connections"].extend([
            edge(clip, AUDIO_REF, bus, BUS_INPUT),
            edge(picture["SourceParentOrChildId"], picture["SourceSlotId"],
                 execute, EXECUTE_INPUT),
            edge(bus, BUS_RESULT, execute, EXECUTE_INPUT),
            edge(execute, EXECUTE_OUTPUT, target, RENDER_COMMAND),
        ])
        ui["SymbolChildUis"].extend([
            {"ChildId": clip, "Position": {"X": 3320.0, "Y": 1610.0}},
            {"ChildId": bus, "Position": {"X": 3570.0, "Y": 1610.0}},
            {"ChildId": execute, "Position": {"X": 3900.0, "Y": 1250.0}},
        ])
        ui["Description"] = (
            "Editable Blender/TiXL dance graph with a 120 BPM soundtrack. "
            "The AudioClip feeds the Soundtrack bus, then Execute pulls both sound "
            "and picture. Move TimeClips and edit mesh, texture, or audio routing here."
        )
        # Keep a local backup before changing the user-owned home graph.
        backup = HERE / ".tixl_cache" / "soundtrack_backup"
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(symbol, backup / symbol.name)
        shutil.copy2(ui_file, backup / ui_file.name)
        write_t3(symbol, home)
        write_t3(ui_file, ui)
        print(f"Installed AudioClip -> AudioBus -> Execute in {symbol}")

    target_asset = project / "Assets" / "audio" / WAV.name
    target_asset.parent.mkdir(parents=True, exist_ok=True)
    if not target_asset.is_file() or file_hash(target_asset) != file_hash(WAV):
        shutil.copy2(WAV, target_asset)
    print(f"Asset: {target_asset}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    install(parser.parse_args().project.resolve())
