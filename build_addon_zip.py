"""Build the Blender install-from-disk ZIP from the committed package."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent
package = root / "tixl_blender_bridge"
output = root / "tixl_blender_bridge.zip"
with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for path in sorted(package.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            archive.write(path, path.relative_to(root))
print(output)
