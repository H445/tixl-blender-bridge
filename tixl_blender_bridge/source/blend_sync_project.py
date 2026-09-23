"""Turn a TiXL-created project scaffold into a generated Blender composition."""
import json
import re
import shutil
import subprocess
import time
from pathlib import Path


def populate(project: Path, graph_files: list[Path], backup_root: Path, editor: Path) -> None:
    project = project.resolve()
    csproj = next(project.glob("*.csproj"), None)
    if csproj is None:
        raise FileNotFoundError(f"No TiXL project scaffold in {project}")
    name = csproj.stem
    symbols = project / "Symbols"
    template = symbols / f"{name}.cs"
    if not template.is_file():
        raise FileNotFoundError(f"No TiXL home symbol in {symbols}")
    text = csproj.read_text(encoding="utf-8")
    home = re.search(r"<HomeGuid>([^<]+)</HomeGuid>", text)
    if home is None:
        raise ValueError("The TiXL project has no release HomeGuid")
    graph = json.loads(graph_files[0].read_text(encoding="utf-8"))
    ui = json.loads(graph_files[1].read_text(encoding="utf-8"))
    root_zero = "00000000-0000-0000-0000-000000000000"
    output_id = next(edge["TargetSlotId"] for edge in graph["Connections"]
                     if edge["TargetParentOrChildId"] == root_zero)
    input_id = graph["Inputs"][0]["Id"]
    graph["Id"] = ui["Id"] = home.group(1)
    source = f'''using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Interfaces;
using T3.Core.Operator.Slots;
using T3.Core.DataTypes.Vector;
using T3.Core.Resource;
using System.Runtime.InteropServices;
namespace PrismalLabs.{name};
[Guid("{home.group(1)}")]
internal sealed class {name} : Instance<{name}>
{{
    [Input(Guid="{input_id}")] public readonly InputSlot<Int2> OutputResolution = new(new Int2(960, 540));
    [Output(Guid="{output_id}")] public readonly Slot<Texture2D> Output = new();
}}
public sealed class ShareDefinition : IShareResources
{{ public bool ShouldShareResources => true; }}
'''
    # A scaffold is created by TiXL and already carries valid release metadata.
    # Preserve it and the original home files before replacing any content.
    backup = backup_root / time.strftime("%Y%m%d_%H%M%S")
    backup.mkdir(parents=True, exist_ok=True)
    for suffix in (".cs", ".t3", ".t3ui"):
        shutil.copy2(symbols / f"{name}{suffix}", backup / f"{name}{suffix}")
    (symbols / f"{name}.cs").write_text(source, encoding="utf-8")
    (symbols / f"{name}.t3").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    (symbols / f"{name}.t3ui").write_text(json.dumps(ui, indent=2), encoding="utf-8")
    subprocess.run(["dotnet", "build", str(csproj), "--no-restore",
                    f"-p:T3_ASSEMBLY_PATH={editor}", "--nologo"], check=True)
