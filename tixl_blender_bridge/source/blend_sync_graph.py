"""Generate a reusable TiXL composition for a saved Blender project.

The graph uses installed BlenderExport operators and stable cache paths.
It is generated data; edit the .blend, not this graph.
"""
import copy
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates"


def generate(blend: Path, cache: Path, manifest: dict) -> list[Path]:
    worlds = manifest["worlds"]
    if not worlds:
        raise ValueError("The Blender export contains no worlds")
    label = re.sub(r"[^A-Za-z0-9]", "", blend.stem.title()) or "BlenderScene"
    short = uuid.uuid5(uuid.NAMESPACE_URL, str(blend.resolve()).lower()).hex[:8]
    class_name = f"Blend{label}{short}"
    namespace = "PrismalLabs.BlenderExport.Generated"
    identity = lambda value: str(uuid.uuid5(uuid.NAMESPACE_URL, str(blend.resolve()).lower() + "/" + value))
    template_ids = json.loads((TEMPLATE / "graph_nodes.json").read_text(encoding="utf-8"))
    core_keys = ["timeline", "scene_switch", "lights", "environment", "camera", "render", "bloom",
            "blur", "material_fill", "passage", "tonemap", "output_blit", "output_target"]
    branch_keys = ["laboratory_opaque_load", "laboratory_opaque_motion", "laboratory_opaque_draw",
                   "laboratory_glass_load", "laboratory_glass_motion", "laboratory_glass_draw",
                   "laboratory_glass_solid_draw", "laboratory"]
    t3 = json.loads((TEMPLATE / "BridgeTemplate.t3").read_text(encoding="utf-8"))
    t3ui = json.loads((TEMPLATE / "BridgeTemplate.t3ui").read_text(encoding="utf-8"))
    template_children = {child["Id"]: child for child in t3["Children"]}
    template_uis = {ui["ChildId"]: ui for ui in t3ui["SymbolChildUis"]}
    template_connections = t3["Connections"]
    core_ids = {template_ids[key]: identity("core/" + key) for key in core_keys}
    branch_template_ids = {template_ids[key] for key in branch_keys}
    t3["Id"] = t3ui["Id"] = identity("symbol")
    old_input = t3["Inputs"][0]["Id"]
    old_output = next(c["TargetSlotId"] for c in t3["Connections"] if c["TargetParentOrChildId"] == "00000000-0000-0000-0000-000000000000")
    new_input = identity("input/resolution")
    new_output = identity("output/image")
    t3["Inputs"][0]["Id"] = new_input
    children = []
    uis = []
    def clone_child(old, new, key, name, y_offset=0):
        child = copy.deepcopy(template_children[old])
        child["Id"] = new
        child["Name"] = child["Name"].replace("Bridge Template", blend.stem).replace("Laboratory", name.title())
        values = {v["Id"]: v for v in child.get("InputValues", [])}
        if key == "timeline":
            values["0713a026-3b7b-5ddf-ac49-e585d8248fa6"]["Value"] = str(cache / "camera_60hz.bin")
            values["70bceb8e-15a0-592f-a01b-ff73dfac2a59"]["Value"] = str(cache / "camera_timeline.json")
        elif key.endswith("_load"):
            part = "glass" if "_glass_" in key else "opaque"
            values["292e80cf-ba31-4a50-9bf4-83712430f811"]["Value"] = str(cache / "worlds" / f"{name}_{part}.glb")
        elif key.endswith("_motion"):
            part = "glass" if "_glass_" in key else "opaque"
            values["ca02f7a3-a03a-4db0-a05d-3a66b0c9ab11"]["Value"] = str(cache / "worlds" / f"{name}_animation.bin")
            values["3a4c36f9-e8c1-4ab7-b370-0f548b054933"]["Value"] = str(cache / "worlds" / f"{name}_{part}.glb")
        elif key == "lights":
            for value in child["InputValues"]:
                if value["Id"] == "a17e4d92-6c38-4f0b-b5d1-2e9a7c8f6043":
                    value["Value"] = ",".join(w["world"] for w in worlds)
                elif value["Id"] == "e0a26c9d-fc85-59a7-88b5-1d1b0d8c5c3f":
                    value["Value"] = str(cache / "worlds")
        children.append(child)
        ui = copy.deepcopy(template_uis[old])
        ui["ChildId"] = new
        ui["Position"]["Y"] += y_offset
        uis.append(ui)
    for key in core_keys:
        old = template_ids[key]
        clone_child(old, core_ids[old], key, blend.stem)
    branch_maps = []
    for index, world in enumerate(worlds):
        name = world["world"]
        keys = ["laboratory"]
        if world["opaque_count"]:
            keys += ["laboratory_opaque_load", "laboratory_opaque_motion", "laboratory_opaque_draw"]
        if world["glass_count"]:
            keys += ["laboratory_glass_load", "laboratory_glass_motion", "laboratory_glass_draw",
                     "laboratory_glass_solid_draw"]
        mapping = {template_ids[key]: identity(f"world/{index}/{key}") for key in keys}
        branch_maps.append(mapping)
        for key in keys:
            old = template_ids[key]
            clone_child(old, mapping[old], key, name, index * 380)
    t3["Children"] = children
    zero = "00000000-0000-0000-0000-000000000000"
    connections = []
    def mapped_edge(edge, mapping):
        result = copy.deepcopy(edge)
        source, target = result["SourceParentOrChildId"], result["TargetParentOrChildId"]
        result["SourceParentOrChildId"] = mapping.get(source, source)
        result["TargetParentOrChildId"] = mapping.get(target, target)
        if source == zero and result["SourceSlotId"] == old_input:
            result["SourceSlotId"] = new_input
        if target == zero and result["TargetSlotId"] == old_output:
            result["TargetSlotId"] = new_output
        return result
    for edge in template_connections:
        source, target = edge["SourceParentOrChildId"], edge["TargetParentOrChildId"]
        if (source == zero or source in core_ids) and (target == zero or target in core_ids):
            connections.append(mapped_edge(edge, core_ids))
    for mapping in branch_maps:
        combined = {**core_ids, **mapping}
        for edge in template_connections:
            source, target = edge["SourceParentOrChildId"], edge["TargetParentOrChildId"]
            if ((source in mapping and target in mapping)
                or (source == template_ids["timeline"] and target in mapping)
                or (source in mapping and target == template_ids["scene_switch"])):
                if (source in combined and target in combined):
                    connections.append(mapped_edge(edge, combined))
    t3["Connections"] = connections
    ordered = sorted(enumerate(worlds), key=lambda pair: pair[1]["active_clip"][0])
    if ordered[0][1]["active_clip"][0] != 1:
        raise ValueError("The first TiXL world must start at source frame 1")
    for (_, before), (_, after) in zip(ordered, ordered[1:]):
        if after["active_clip"][0] > before["active_clip"][1] + 1:
            raise ValueError("Gap between TiXL world clips")
    curve = copy.deepcopy(t3["Animator"][0])
    curve["InstanceId"] = core_ids[template_ids["timeline"]]
    curve["Curve"]["Keys"] = [{"Time": (world["active_clip"][0] - 1) / 120,
                                 "Value": float(index), "InInterpolation": "Constant",
                                 "OutInterpolation": "Constant"} for index, world in ordered]
    t3["Animator"] = [curve] if len(worlds) > 1 else []
    t3["ProjectSettings"]["Export"]["Title"] = blend.stem
    t3ui["Description"] = f"Generated from {blend.name}. Edit and save the Blender file; Prismal TiXL Auto Sync rebuilds the runtime cache and this composition."
    t3ui["SymbolChildUis"] = uis
    t3ui["Sections"] = []
    t3ui["InputUis"][0]["InputId"] = new_input
    t3ui["OutputUis"][0]["OutputId"] = new_output
    t3ui["Settings"]["Timeline"]["SourceExtentEnd"] = max(1.0, (max(w["active_clip"][1] for w in worlds) - 1) / 120)
    out = cache / "native_source"
    out.mkdir(parents=True, exist_ok=True)
    files = [out / f"{class_name}.t3", out / f"{class_name}.t3ui", out / f"{class_name}.cs"]
    files[0].write_text(json.dumps(t3, indent=2), encoding="utf-8")
    files[1].write_text(json.dumps(t3ui, indent=2), encoding="utf-8")
    files[2].write_text(f'''using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Slots;
using T3.Core.DataTypes.Vector;
using T3.Core.Resource;
using System.Runtime.InteropServices;
namespace {namespace};
[Guid("{t3['Id']}")]
internal sealed class {class_name} : Instance<{class_name}>
{{
    [Input(Guid="{new_input}")] public readonly InputSlot<Int2> OutputResolution = new(new Int2(960, 540));
    [Output(Guid="{new_output}")] public readonly Slot<Texture2D> Output = new();
}}
''', encoding="utf-8")
    (out / "graph_summary.json").write_text(json.dumps({"blend": str(blend), "symbol": t3["Id"],
        "class": namespace + "." + class_name, "operators": len(t3["Children"]),
        "connections": len(t3["Connections"])}, indent=2), encoding="utf-8")
    return files
