# Blender → TiXL Bridge

Edit a scene in Blender, save its `.blend`, and let the bridge build the TiXL version in the background. **The `.blend` is the file you manage.** GLB meshes, animation data, camera samples, lights, and a TiXL graph are generated caches.

This repository contains the Blender add-on and three reusable TiXL operators: **Blender Animation Scene**, **Blender Camera Timeline**, and **Blender Export Lights**. They are shared by every generated project; none is tied to a particular demo.

## Set up once (Windows)

You need Blender 4.3 or newer (tested with 5.2), a built TiXL Editor, a TiXL C# operator project, and the .NET SDK. Create the operator project once in TiXL so it has valid release metadata. You can then close TiXL; **the debug server is not needed**.

1. Download or clone this repository. In Blender, open **Edit → Preferences → Add-ons → Install from Disk**, choose **`tixl_blender_bridge.zip`**, and enable **Prismal Labs Blender → TiXL Bridge**. (In Blender versions that call it **Get Extensions**, use **Install from Disk** there.)
2. Open the add-on preferences and set **TiXL operator project** to the folder containing your TiXL `.csproj` and `Symbols` folder. Set **TiXL Editor folder** to the build folder containing `TiXL.exe`.
3. Open any Blender project with an active camera. In **Scene Properties → TiXL Bridge**, turn on **Sync after save**. Save the `.blend`.

The first save can take a while. Watch `<blend folder>/.tixl_cache/<blend name>/sync_logs/latest.log`. The bridge installs the operators, creates a TiXL project for this `.blend` from your TiXL-created project scaffold, and builds it. TiXL starts without a debug server; **select the generated project once in TiXL**. It is created beside the operator project, and its exact path is recorded in `.tixl_cache/<blend name>/tixl_project.json`. Later Blender saves rebuild changed content automatically. TiXL may restart to load new files, so save any open TiXL work first. The **Sync saved .blend to TiXL** button runs the same process on demand.

**Daily use:** work in Blender and save. You do not need to export or import binary files by hand. A failed rebuild keeps the previous validated cache.

## What comes across

- Meshes and UV textures in GLB; PBR material properties supported by Blender's glTF export.
- Object transforms, visibility, shape keys, material color and emission, and lights sampled at 60 Hz.
- The active camera, including camera-bound timeline markers for cuts.
- A generated TiXL graph with one branch per Blender world, camera movement, scene switching, rendering, and final output resolution control.

By default the active Blender scene is one TiXL world. To use several worlds, add a **Scene custom property** named `tixl_worlds` containing JSON like this:

```json
[
  {"name":"lab","collection":"Lab","start_seconds":0,"end_seconds":30},
  {"name":"culture","collection":"Culture","start_seconds":30,"end_seconds":60}
]
```

The named collections must exist. Keep the time ranges contiguous; the generated graph switches branches at their boundaries. Camera markers can control the view independently.

## Where things go

The authored `.blend` stays where you saved it. Generated data, logs, and the TiXL project link live in `.tixl_cache/<blend name>/` beside it. A newly generated TiXL project is created beside the operator project. **Do not edit generated graphs or cache files**; the next save may replace them.

This is a save-driven build, not direct `.blend` playback inside TiXL. Blender shaders and World nodes that glTF cannot represent need TiXL-side equivalents. In particular, arbitrary procedural materials and physical refraction are not guaranteed to match Blender.

## Command line / troubleshooting

The Blender add-on runs `tixl_blender_bridge/source/blend_sync.py` using Blender's bundled Python. For a cache-only build, set `TIXL_BRIDGE_BLENDER` to your Blender executable and run:

```powershell
python tixl_blender_bridge/source/blend_sync.py sync --blend C:\path\scene.blend --no-install
```

`status --blend ...` checks whether the cache matches the saved file. `--force` rebuilds even when the source hash matches. A full command-line TiXL installation also needs `TIXL_BRIDGE_OPERATOR_PROJECT` and `TIXL_BRIDGE_EDITOR` set to the same folders used in the add-on preferences. Set `TIXL_BRIDGE_LAUNCH_EDITOR=0` if you want the bridge to build files without starting TiXL.

If a save does not appear in TiXL, check `sync_logs/latest.log` first. Missing cameras, missing collections, and a project without release metadata are reported there. Newly created projects require a one-time selection in TiXL; the bridge does not remotely control the editor.

## Package layout

- `tixl_blender_bridge/__init__.py` — Blender add-on and save handler.
- `tixl_blender_bridge/operators/` — reusable TiXL `.cs`, `.t3`, `.t3ui` operators.
- `tixl_blender_bridge/source/` — exporter, validation, graph generation, and TiXL installation.
- `tixl_blender_bridge/templates/` — internal graph template; never install it as a TiXL project.
- `build_addon_zip.py` — reproduces the installable ZIP.

The add-on currently targets Windows TiXL builds. Its background exporter does not run during TiXL render frames.
