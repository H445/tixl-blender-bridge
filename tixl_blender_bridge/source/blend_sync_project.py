"""Turn a TiXL-created project scaffold into a generated Blender composition."""
import json
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path


def create_scaffold(project: Path, name: str, template: Path, blend: Path) -> None:
    """Create a TiXL project from a TiXL-created project, without the editor API."""
    csproj = project / f"{name}.csproj"
    if csproj.is_file():
        return
    if project.exists() and any(project.iterdir()):
        raise FileExistsError(f"Refusing to replace nonempty TiXL project: {project}")
    template_csproj = next(template.glob("*.csproj"), None)
    if template_csproj is None:
        raise FileNotFoundError(f"No TiXL project template in {template}")
    text = template_csproj.read_text(encoding="utf-8")
    values = {
        "RootNamespace": f"PrismalLabs.{name}",
        "HomeGuid": str(uuid.uuid5(uuid.NAMESPACE_URL, str(blend.resolve()).lower() + "/home")),
        "PackageId": str(uuid.uuid5(uuid.NAMESPACE_URL, str(blend.resolve()).lower() + "/package")),
    }
    for key, value in values.items():
        text, count = re.subn(rf"<{key}>[^<]*</{key}>", f"<{key}>{value}</{key}>", text, count=1)
        if count != 1:
            raise ValueError(f"TiXL template is missing {key}: {template_csproj}")
    project.mkdir(parents=True, exist_ok=True)
    for folder in ("Symbols", "Assets", "dependencies"):
        (project / folder).mkdir(exist_ok=True)
    props = template / "Directory.Build.props"
    if props.is_file():
        shutil.copy2(props, project / props.name)
    csproj.write_text(text, encoding="utf-8")


def populate(project: Path, graph_files: list[Path], backup_root: Path, editor: Path) -> None:
    project = project.resolve()
    csproj = next(project.glob("*.csproj"), None)
    if csproj is None:
        raise FileNotFoundError(f"No TiXL project scaffold in {project}")
    name = csproj.stem
    symbols = project / "Symbols"
    symbols.mkdir(parents=True, exist_ok=True)
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
    # Preserve any prior generated home files before replacing them.
    existing = [symbols / f"{name}{suffix}" for suffix in (".cs", ".t3", ".t3ui")]
    if any(path.is_file() for path in existing):
        backup = backup_root / time.strftime("%Y%m%d_%H%M%S")
        backup.mkdir(parents=True, exist_ok=True)
        for path in existing:
            if path.is_file():
                shutil.copy2(path, backup / path.name)
    (symbols / f"{name}.cs").write_text(source, encoding="utf-8")
    (symbols / f"{name}.t3").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    (symbols / f"{name}.t3ui").write_text(json.dumps(ui, indent=2), encoding="utf-8")
    subprocess.run(["dotnet", "build", str(csproj),
                    f"-p:T3_ASSEMBLY_PATH={editor}", "--nologo"], check=True)
