"""Build the Blender install-from-disk ZIP from the committed package."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent
package = root / "blender_tixl_bridge"
output = root / "blender_tixl_bridge.zip"
with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for path in sorted(package.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            archive.write(path, path.relative_to(root))
    for name in ("BlendShapeExample.blend", "README.md", "build_blend_shape_example.py",
                 "validate_blend_shape_example.py"):
        archive.write(root / "examples" / name,
                      "blender_tixl_bridge/examples/" + name)
print(output)
