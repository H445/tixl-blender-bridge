# Two-minute breakdance bridge example

![MPFB character in the handstand-kick section](breakdance_handstand.png)

`humanoid_breakdance.blend` is a 120-second, 60 fps performance by a textured
MPFB/MakeHuman character. Ten CMU motion capture takes drive the dance. The
Blender scene contains an editable **163-bone MPFB default rig**, including
individual finger and toe bones, in the hidden `Authoring` collection. Unhide
that collection and hide the visible `Move` collections to inspect or edit the
skeletal animation without seeing overlapping characters. Finger motion is
added in the builder: CMU's source recordings did not capture fingers.

The visible `Move 01` through `Move 10` collections hold morph-baked versions
of the character for the current TiXL bridge runtime. Adjacent short moves
share a world, giving eight TiXL worlds for ten moves. All used textures are
packed in the `.blend`.

| Time | Move | CMU take |
| --- | --- | --- |
| 0:00–0:13 | Upright opening | 85_03 |
| 0:13–0:28 | Fancy footwork | 85_04 |
| 0:28–0:40 | Helicopter | 85_08 |
| 0:40–0:50 | Handstand kicks | 85_05 |
| 0:50–1:00 | Kick flip | 85_06 |
| 1:00–1:04 | Motorcycle freeze | 85_09 |
| 1:04–1:18 | Upright variation | 85_11 |
| 1:18–1:36 | Long break combo | 85_12 |
| 1:36–1:54 | Break sequence with flips | 85_14 |
| 1:54–2:00 | Finale | 85_10 |

## Open and sync

Open `humanoid_breakdance.blend` in Blender and play frames 1–7201. Timeline
markers name the moves and switch among three studio cameras. The bridge add-on
has **Auto sync on save** enabled in this scene. In its preferences, select the
operator project and **Debug bridge**. Use **Sync saved .blend to TiXL** to
regenerate the runtime cache and open the generated TiXL project. You can also
run this from the repository root:

```powershell
python tixl_blender_bridge/source/blend_sync.py sync --blend examples/humanoid_breakdance.blend --profile generic
```

The bridge writes the generated project location to
`examples/.tixl_cache/humanoid_breakdance/tixl_project.json`. On this
workstation, it uses the TiXL user folder and root namespace
`PrismalLabs.TixlBlenderBridge`. The cache is generated output ignored by Git.
At 120 BPM, the TiXL composition lasts 60 bars (120 seconds).

## Rebuild

`build_breakdance.py` rebuilds the Blender scene from the source BVH files in
`mocap/`. It needs Blender 5.2, [MPFB](https://extensions.blender.org/add-ons/mpfb/),
and the CC0 [MakeHuman system assets and skins02 packs](https://static.makehumancommunity.org/assets/assetpacks.html)
installed through MPFB. Run:

```powershell
blender --background --python examples/build_breakdance.py
```

The builder drives both deform bones of each upper arm and forearm from the
captured limb direction while preserving the MPFB rig's anatomical bone roll.
The source BVH has zero-length hand bones, so the wrists follow the forearms
instead of inheriting unreliable hand rotations. The first frame is the capture's
T-pose reference. `breakdance_tpose.png`, `breakdance_tpose_side.png`, and
`breakdance_tpose_elevated.png` show it from three angles; the other
`breakdance_*.png` files sample the dance in Blender.

After rebuilding, check the T-pose and dance frames with:

```powershell
blender --background examples/humanoid_breakdance.blend --python examples/validate_breakdance.py
```

This check compares the saved rig against the BVH arm directions, verifies
neutral wrist rotation and T-pose limb placement, and checks floor contact at
0, 2, 45, 83, 100, and 116 seconds. `tixl_breakdance_*.png` are corresponding
screenshots captured through TiXL's debug bridge after export.

The source recordings are CMU Graphics Lab [subject 85](https://mocap.cs.cmu.edu/search.php?subjectnumber=85),
converted to BVH by Bruce Hahn. CMU permits use of the motions in projects,
including commercial projects, while prohibiting resale of the motion data
itself. See the [CMU database terms](https://mocap.cs.cmu.edu/) and the
[conversion repository](https://github.com/una-dinosauria/cmu-mocap).
