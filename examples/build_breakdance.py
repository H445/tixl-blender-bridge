"""Build a two-minute, ten-move, motion-captured MPFB breakdance scene.

Requires Blender 5.2, MPFB, and the CC0 MakeHuman system assets + skins02
packs. CMU BVH recordings are stored in examples/mocap. Packed textures and
baked deformation make the saved .blend self-contained for playback and sync.

Run: blender --background --python examples/build_breakdance.py
"""

import json
import sys
from math import ceil, pi, sin
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nightclub_set import decorate


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "humanoid_breakdance.blend"
FPS = 60
POSES_PER_SECOND = 8
# Durations sum to exactly 120 seconds. Each section uses a different CMU
# subject 85 take and has its own TiXL world to keep morph meshes manageable.
MOVES = (
    ("03", "Upright opening", 13),
    ("04", "Fancy footwork", 15),
    ("08", "Helicopter", 12),
    ("05", "Handstand kicks", 10),
    ("06", "Kick flip", 10),
    ("09", "Motorcycle freeze", 4),
    ("11", "Upright variation", 14),
    ("12", "Long break combo", 18),
    ("14", "Break sequence with flips", 18),
    ("10", "Finale", 6),
)
assert sum(move[2] for move in MOVES) == 120
END = 120 * FPS + 1

bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mpfb")
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.locationservice import LocationService
from bl_ext.blender_org.mpfb.services.targetservice import TargetService

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.name = "MPFB Human | Breakdance Set | TiXL Bridge"
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = END
scene.render.film_transparent = False
scene.world.color = (0.14, 0.14, 0.14)

data_root = Path(LocationService.get_user_data())
needed = (
    "skins/mindfront_aksel_skin/mindfront_aksel_skin.mhmat",
    "eyes/high-poly/high-poly.mhclo",
    "eyes/materials/brown_eye.png",
    "eyebrows/eyebrow001/eyebrow001.mhclo",
    "eyelashes/eyelashes01/eyelashes01.mhclo",
    "hair/short01/short01.mhclo",
    "clothes/male_casualsuit03/male_casualsuit03.mhclo",
    "clothes/shoes01/shoes01.mhclo",
)
for relative in needed:
    if not (data_root / relative).is_file():
        raise FileNotFoundError(f"MPFB asset pack missing {relative} in {data_root}")

macro = TargetService.get_default_macro_info_dict()
macro.update(gender=0.92, age=0.53, height=0.56, weight=0.50, muscle=0.55)
macro["race"] = {"caucasian": 0.85, "asian": 0.10, "african": 0.05}
human = HumanService.create_human(feet_on_ground=True, scale=0.1,
                                  macro_detail_dict=macro)
human.name = "Human | MPFB anatomical mesh"
rig = HumanService.add_builtin_rig(human, "default")
rig.name = "Authoring rig | MPFB default | 163 bones"
HumanService.set_character_skin(str(data_root / needed[0]), human,
                                skin_type="GAMEENGINE")

assets = [("Eyes", "eyes/high-poly/high-poly.mhclo"),
          ("Eyebrows", "eyebrows/eyebrow001/eyebrow001.mhclo"),
          ("Eyelashes", "eyelashes/eyelashes01/eyelashes01.mhclo"),
          ("Hair", "hair/short01/short01.mhclo"),
          ("Clothes", "clothes/male_casualsuit03/male_casualsuit03.mhclo"),
          ("Clothes", "clothes/shoes01/shoes01.mhclo")]
source_meshes = [human]
for kind, relative in assets:
    source_meshes.append(HumanService.add_mhclo_asset(
        str(data_root / relative), human, asset_type=kind,
        subdiv_levels=0, material_type="GAMEENGINE"))


def textured_material(name, diffuse, normal=None, roughness=0.62,
                      subsurface=0.0, alpha=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Subsurface Weight"].default_value = subsurface
    mat.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    color = nodes.new("ShaderNodeTexImage")
    color.image = bpy.data.images.load(str(data_root / diffuse), check_existing=True)
    mat.node_tree.links.new(color.outputs["Color"], shader.inputs["Base Color"])
    if normal:
        image = nodes.new("ShaderNodeTexImage")
        image.image = bpy.data.images.load(str(data_root / normal), check_existing=True)
        image.image.colorspace_settings.name = "Non-Color"
        normal_node = nodes.new("ShaderNodeNormalMap")
        normal_node.inputs["Strength"].default_value = 0.7
        mat.node_tree.links.new(image.outputs["Color"], normal_node.inputs["Color"])
        mat.node_tree.links.new(normal_node.outputs["Normal"], shader.inputs["Normal"])
    if alpha:
        mat.node_tree.links.new(color.outputs["Alpha"], shader.inputs["Alpha"])
        mat.surface_render_method = "DITHERED"
    mat.diffuse_color = (0.7, 0.7, 0.7, 1.0)
    return mat


materials = [
    textured_material("Skin | Aksel CC0", "skins/mindfront_aksel_skin/Aksel_Skin_diffuse.png",
                      "skins/mindfront_aksel_skin/Aksel_Skin_NRM.png", 0.7, 0.07),
    textured_material("Eyes | brown CC0", "eyes/materials/brown_eye.png", roughness=0.14),
    textured_material("Brows | CC0", "eyebrows/eyebrow001/eyebrow001.png",
                      roughness=0.82, alpha=True),
    textured_material("Lashes | CC0", "eyelashes/eyelashes01/eyelashes01.png",
                      roughness=0.82, alpha=True),
    textured_material("Hair | short dark CC0", "hair/short01/short01_diffuse.png",
                      roughness=0.75, alpha=True),
    textured_material("Shirt and jeans | CC0", "clothes/male_casualsuit03/male_casualsuit03_diffuse.png",
                      "clothes/male_casualsuit03/male_casualsuit03_normal.png", 0.78),
    textured_material("Shoes | CC0", "clothes/shoes01/shoes01_diffuse.png",
                      "clothes/shoes01/shoes01_normal.png", 0.7),
]
for obj, mat in zip(source_meshes, materials):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


MAPPING = {
    "Hips": "root",
    "LHipJoint": "pelvis.L", "RHipJoint": "pelvis.R",
    "LeftUpLeg": "upperleg01.L", "RightUpLeg": "upperleg01.R",
    "LeftLeg": "lowerleg01.L", "RightLeg": "lowerleg01.R",
    "LeftFoot": "foot.L", "RightFoot": "foot.R",
    "LeftToeBase": "toe1-1.L", "RightToeBase": "toe1-1.R",
    "LowerBack": "spine05", "Spine": "spine03", "Spine1": "spine02",
    "Neck": "neck01", "Neck1": "neck03", "Head": "head",
    "LeftShoulder": "clavicle.L", "RightShoulder": "clavicle.R",
    "LeftArm": "upperarm01.L", "RightArm": "upperarm01.R",
    "LeftForeArm": "lowerarm01.L", "RightForeArm": "lowerarm01.R",
}


def bvh_frames(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("Frames:"):
                return int(line.split(":", 1)[1])
    raise ValueError(f"Missing BVH frame count: {path}")


def reset_target_rig():
    rig.location = (0, 0, 0)
    for bone in rig.pose.bones:
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()


SOURCE_FOR_TARGET = {target: source for source, target in MAPPING.items()}
# The MPFB rig splits each anatomical limb into two deform bones. Drive both
# pieces from the same captured segment so the elbow/knee does not point back
# through the torso when the source and target rest-pose axes differ.
for side, source_side in (("L", "Left"), ("R", "Right")):
    SOURCE_FOR_TARGET[f"shoulder01.{side}"] = f"{source_side}Shoulder"
    SOURCE_FOR_TARGET[f"upperarm02.{side}"] = f"{source_side}Arm"
    SOURCE_FOR_TARGET[f"lowerarm02.{side}"] = f"{source_side}ForeArm"
    SOURCE_FOR_TARGET[f"upperleg02.{side}"] = f"{source_side}UpLeg"
    SOURCE_FOR_TARGET[f"lowerleg02.{side}"] = f"{source_side}Leg"

# These segments need the BVH direction, but copying the source bone's full
# quaternion also copies its roll. That rolled the target ankles and forearms.
DIRECTIONAL_BONES = ("upperarm", "lowerarm", "upperleg", "lowerleg", "foot", "toe1-1")


def bone_depth(bone):
    depth = 0
    while bone.parent:
        bone = bone.parent
        depth += 1
    return depth


TARGET_BONES = sorted(rig.data.bones, key=bone_depth)


def retarget(capture, source_frame):
    whole = int(source_frame)
    scene.frame_set(whole, subframe=source_frame - whole)
    rig.location = (0, 0, 0)
    orientations = {}
    for bone in TARGET_BONES:
        rest = bone.matrix_local.to_quaternion()
        if bone.parent:
            parent_rest = bone.parent.matrix_local.to_quaternion()
            base = orientations[bone.parent.name] @ parent_rest.inverted() @ rest
        else:
            base = rest
        source_name = SOURCE_FOR_TARGET.get(bone.name)
        if source_name:
            source_bone = capture.pose.bones[source_name]
            source_rest = source_bone.bone.matrix_local.to_quaternion()
            desired = source_bone.matrix.to_quaternion() @ source_rest.inverted() @ rest
            if bone.name == "root":
                # The capture hip orientation carries whole-body inversions.
                desired = source_bone.matrix.to_quaternion()
            elif bone.name.startswith(DIRECTIONAL_BONES):
                # Apply the captured swing while keeping MPFB's anatomical
                # roll. A full source quaternion twists wrists, ankles and
                # the shirt; an uncorrected rest delta crosses the arms.
                source_direction = (source_bone.tail - source_bone.head).normalized()
                target_direction = desired @ Vector((0, 1, 0))
                desired = target_direction.rotation_difference(source_direction) @ desired
            relative = base.inverted() @ desired
            rig.pose.bones[bone.name].rotation_quaternion = relative
            orientations[bone.name] = desired
        else:
            # The BVH hands have zero-length bones and unreliable roll. The
            # MPFB wrists retain their neutral relation to each forearm.
            rig.pose.bones[bone.name].rotation_quaternion = (1, 0, 0, 0)
            orientations[bone.name] = base
    # CMU did not capture finger joints. Add a relaxed hand shape in the air
    # and open the fingers as the hands approach the floor for support.
    t = source_frame / 120
    for side, source_hand in (("L", "LeftHand"), ("R", "RightHand")):
        hand_height = capture.pose.bones[source_hand].tail.z
        support = max(0.0, min(1.0, (0.35 - hand_height) / 0.28))
        curl = 0.34 * (1.0 - support) + 0.06 * support
        curl += 0.055 * sin(2 * pi * 1.3 * t + (0 if side == "L" else 1.2))
        for digit in range(1, 6):
            for segment in range(1, 4):
                bone = rig.pose.bones[f"finger{digit}-{segment}.{side}"]
                factor = (0.50, 0.90, 0.65)[segment - 1]
                if digit == 1:
                    factor *= 0.6
                world_turn = Quaternion(Vector((1, 0, 0)), curl * factor)
                rest = bone.bone.matrix_local.to_quaternion()
                bone.rotation_quaternion = rest.inverted() @ world_turn @ rest
    bpy.context.view_layer.update()
    return capture.pose.bones["Hips"].head.copy()


def set_visibility(obj, start, end):
    # Each move owns [start, end); the last move also owns the final frame.
    # This prevents two bodies overlapping at a shared-world cut.
    points = {1: start != 1, start: False, end: end != END, END: end != END}
    if start > 1:
        points[start - 1] = True
    if end < END:
        points[end + 1] = True
    for frame, hidden in sorted(points.items()):
        obj.hide_render = hidden
        obj.hide_viewport = hidden
        obj.keyframe_insert(data_path="hide_render", frame=frame)
        obj.keyframe_insert(data_path="hide_viewport", frame=frame)
    obj.hide_render = start != 1
    obj.hide_viewport = start != 1


worlds = []
move_collections = []
cursor_seconds = 0
for move_index, (take, title, seconds) in enumerate(MOVES):
    bvh_path = HERE / "mocap" / f"85_{take}.bvh"
    if not bvh_path.is_file():
        raise FileNotFoundError(bvh_path)
    capture_frames = bvh_frames(bvh_path)
    start = cursor_seconds * FPS + 1
    end = (cursor_seconds + seconds) * FPS + 1
    world_name = f"move{move_index + 1:02d}_{take}"
    collection = bpy.data.collections.new(f"Move {move_index + 1:02d} | {title}")
    scene.collection.children.link(collection)
    collection["mocap_take"] = f"CMU subject 85 trial {take}"
    collection["source_seconds"] = (capture_frames - 1) / 120
    move_collections.append(collection)
    worlds.append({"name": world_name, "collection": collection.name,
                   "start_seconds": cursor_seconds,
                   "end_seconds": cursor_seconds + seconds})
    marker = scene.timeline_markers.new(f"{move_index + 1:02d} | {title}", frame=start)

    reset_target_rig()
    root = bpy.data.objects.new(f"Move {move_index + 1:02d} | motion root", None)
    collection.objects.link(root)
    baked = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for source in source_meshes:
        base = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph),
                                              preserve_all_data_layers=True,
                                              depsgraph=depsgraph)
        obj = bpy.data.objects.new(f"Move {move_index + 1:02d} | {source.name}", base)
        collection.objects.link(obj)
        obj.parent = root
        obj.matrix_world = source.matrix_world.copy()
        obj.shape_key_add(name="Basis", from_mix=False)
        baked.append(obj)

    bpy.ops.import_anim.bvh(filepath=str(bvh_path), global_scale=0.05,
                            frame_start=1)
    capture = bpy.context.object
    capture.name = f"Temporary capture 85_{take}"
    first_hip = retarget(capture, 1.0)
    sample_count = ceil(seconds * POSES_PER_SECOND)
    sample_frames = []
    for sample_index in range(sample_count + 1):
        fraction = sample_index / sample_count
        source_frame = 1 + (capture_frames - 1) * fraction
        output_frame = start + round(seconds * FPS * fraction)
        sample_frames.append(output_frame)
        hip = retarget(capture, source_frame)
        lowest_mesh_z = float("inf")
        depsgraph.update()
        for source, obj in zip(source_meshes, baked):
            evaluated = source.evaluated_get(depsgraph)
            sample = bpy.data.meshes.new_from_object(
                evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
            if len(sample.vertices) != len(obj.data.vertices):
                raise RuntimeError(f"Topology changed in {source.name} at {source_frame}")
            key = obj.shape_key_add(name=f"Pose {sample_index:03d}", from_mix=False)
            coords = [0.0] * (3 * len(sample.vertices))
            sample.vertices.foreach_get("co", coords)
            key.data.foreach_set("co", coords)
            transform = source.matrix_world
            if abs(transform[2][0]) > 1e-6 or abs(transform[2][1]) > 1e-6 or transform[2][2] <= 0:
                raise RuntimeError(f"Unexpected mesh transform on {source.name}")
            lowest_mesh_z = min(lowest_mesh_z,
                                transform[2][2] * min(coords[2::3]) + transform[2][3])
            bpy.data.meshes.remove(sample)
        source_lowest, contact_bone = min(
            (min(bone.head.z, bone.tail.z), bone.name)
            for bone in capture.pose.bones)
        inverted = (capture.pose.bones["Head"].head.z
                    < capture.pose.bones["Hips"].head.z - 0.2)
        hand_contact = inverted and any(name in contact_bone
                                        for name in ("Hand", "Thumb", "Finger"))
        # BVH joint positions sit inside the skin, and the capture's absolute
        # floor drifts between takes. Keep support poses grounded and retain
        # a small clearance for actual airborne moments.
        clearance = 0.0 if hand_contact else min(0.16, max(0.0, source_lowest - 0.08))
        root.location = (hip.x - first_hip.x,
                         hip.y - first_hip.y,
                         clearance - lowest_mesh_z)
        root.keyframe_insert(data_path="location", frame=output_frame)
        # Retain an editable 163-bone animation in Blender alongside the
        # morph-baked meshes used by the current TiXL runtime.
        for name in SOURCE_FOR_TARGET:
            rig.pose.bones[name].keyframe_insert(
                data_path="rotation_quaternion", frame=output_frame)
        for side in ("L", "R"):
            for digit in range(1, 6):
                for segment in range(1, 4):
                    rig.pose.bones[f"finger{digit}-{segment}.{side}"].keyframe_insert(
                        data_path="rotation_quaternion", frame=output_frame)
        rig.location = root.location.copy()
        rig.keyframe_insert(data_path="location", frame=output_frame)
        rig.location = (0, 0, 0)
        if sample_index % 32 == 0:
            print(f"BAKED_MOVE {move_index + 1}/10 pose {sample_index}/{sample_count}", flush=True)

    for obj in baked:
        keys = list(obj.data.shape_keys.key_blocks)[1:]
        for key_index, key in enumerate(keys):
            for neighbor in (key_index - 1, key_index, key_index + 1):
                if 0 <= neighbor < len(keys):
                    key.value = 1.0 if neighbor == key_index else 0.0
                    key.keyframe_insert(data_path="value", frame=sample_frames[neighbor])
            key.value = 0.0
        action = obj.data.shape_keys.animation_data.action
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for point in curve.keyframe_points:
                            point.interpolation = "LINEAR"
        set_visibility(obj, start, end)
    bpy.data.objects.remove(capture, do_unlink=True)
    cursor_seconds += seconds
    print(f"MOVE_COMPLETE {move_index + 1}/10 {title} {start}-{end}", flush=True)


def combine_worlds(first, last):
    group = bpy.data.collections.new(f"TiXL section | moves {first + 1:02d}-{last + 1:02d}")
    scene.collection.children.link(group)
    for collection in move_collections[first:last + 1]:
        group.children.link(collection)
        scene.collection.children.unlink(collection)
    return {"name": f"section{first + 1:02d}_{last + 1:02d}",
            "collection": group.name,
            "start_seconds": worlds[first]["start_seconds"],
            "end_seconds": worlds[last]["end_seconds"]}


# TiXL's library Switch renders at most eight scene inputs. The two short
# adjacent pairs share worlds; their object visibility tracks still cut at
# the individual move boundaries.
worlds = [*worlds[:4], combine_worlds(4, 5), *worlds[6:8],
          combine_worlds(8, 9)]

authoring = bpy.data.collections.new("Authoring | MPFB 163-bone rig and clothed character")
scene.collection.children.link(authoring)
for obj in [rig, *source_meshes]:
    authoring.objects.link(obj)
    if obj.name in scene.collection.objects:
        scene.collection.objects.unlink(obj)
authoring.hide_render = True
authoring.hide_viewport = True
scene["tixl_worlds"] = json.dumps(worlds)


def plain_material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1)
    return mat


floor_mat = plain_material("Backdrop | warm gray", (0.29, 0.305, 0.315), 0.92)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.012))
floor = bpy.context.object
floor.name = "Studio | matte floor"
floor.data.materials.append(floor_mat)


def area_light(name, location, power, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 0.95)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


lights = [
    area_light("Studio | key softbox", (2.2, -3.1, 3.7), 520, 3.2, (1.0, 0.92, 0.84)),
    area_light("Studio | cool fill", (-2.9, -1.1, 2.6), 300, 2.8, (0.77, 0.87, 1.0)),
    area_light("Studio | hair rim", (-1.4, 2.1, 3.2), 500, 2.0, (1.0, 0.97, 0.91)),
]
for collection in move_collections:
    for obj in (floor, *lights):
        collection.objects.link(obj)


def studio_camera(name, location, target, lens):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    data.lens = lens
    data.clip_end = 100
    return obj


cameras = (
    studio_camera("Camera | full front", (3.0, -7.2, 2.5), (0, 0, 1.0), 52),
    studio_camera("Camera | side", (6.6, -3.3, 2.4), (0, 0, 0.95), 52),
    studio_camera("Camera | elevated", (-1.9, -6.5, 4.1), (0, 0, 0.7), 52),
)
scene.camera = cameras[0]
for index, marker in enumerate(sorted(scene.timeline_markers, key=lambda m: m.frame)):
    marker.camera = cameras[(0, 0, 1, 0, 2, 1, 0, 2, 1, 0)[index]]
decorate(scene)
scene.view_settings.view_transform = "AgX"
scene.frame_set(1)

for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        image.pack()
if hasattr(scene, "tixl_bridge_autosync"):
    scene.tixl_bridge_autosync = True
    # Saving a newly generated blend is followed by an explicit verified sync.
    for handler in list(bpy.app.handlers.save_post):
        if getattr(handler, "__module__", "").endswith("tixl_blender_bridge"):
            bpy.app.handlers.save_post.remove(handler)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
print(f"BREAKDANCE_SAVED {OUTPUT} moves={len(MOVES)} seconds=120 rig_bones={len(rig.data.bones)}", flush=True)
