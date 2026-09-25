"""Check the saved rig's reference pose, limbs, and floor contact.

Run: blender --background examples/humanoid_breakdance.blend --python examples/validate_breakdance.py
"""

from math import degrees
from pathlib import Path

import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
scene = bpy.context.scene
rig = bpy.data.objects["Authoring rig | MPFB default | 163 bones"]


def bvh_frames(path):
    with path.open(encoding="utf-8") as stream:
        return next(int(line.split(":", 1)[1]) for line in stream
                    if line.startswith("Frames:"))


def direction(start, end):
    return (end - start).normalized()


for second, take, move_start, duration, move_index in (
    (0, "03", 0, 13, 1),
    (2, "03", 0, 13, 1),
    (45, "05", 40, 10, 4),
    (83, "12", 78, 18, 8),
    (100, "14", 96, 18, 9),
    (116, "10", 114, 6, 10),
):
    scene.frame_set(second * 60 + 1)
    joints = {}
    for side in ("L", "R"):
        upper = rig.pose.bones[f"upperarm01.{side}"]
        elbow = rig.pose.bones[f"lowerarm01.{side}"]
        wrist = rig.pose.bones[f"wrist.{side}"]
        joints[side] = (upper.head.copy(), elbow.head.copy(), wrist.head.copy())

    lateral = direction(joints["R"][0], joints["L"][0])
    center = (joints["L"][0] + joints["R"][0]) * 0.5
    for side, sign in (("L", 1), ("R", -1)):
        for joint in joints[side][1:]:
            assert (joint - center).dot(lateral) * sign > 0.025, (
                f"At {second}s, the {side} arm crosses the torso")
        wrist = rig.pose.bones[f"wrist.{side}"]
        assert wrist.rotation_quaternion.angle < 0.05, (
            f"At {second}s, the {side} wrist has unwanted local twist")

    if second == 0:
        for side, sign in (("L", 1), ("R", -1)):
            ankle = rig.pose.bones[f"foot.{side}"].head
            assert (ankle - center).dot(lateral) * sign > 0.07, (
                f"T-pose {side} ankle crosses the body center")
            forearm = direction(joints[side][1], joints[side][2])
            finger = rig.pose.bones[f"finger3-1.{side}"].tail
            hand = direction(joints[side][2], finger)
            assert forearm.dot(hand) > 0.4, f"T-pose {side} hand bends unnaturally"
        left_foot = rig.pose.bones["foot.L"]
        right_foot = rig.pose.bones["foot.R"]
        assert direction(left_foot.head, left_foot.tail).dot(
            direction(right_foot.head, right_foot.tail)) > 0.5, (
                "T-pose feet point in incompatible directions")
        torso = direction(rig.pose.bones["spine05"].head,
                          rig.pose.bones["spine01"].tail)
        assert torso.dot(Vector((0, 0, 1))) > 0.8, "T-pose torso is twisted"

    depsgraph = bpy.context.evaluated_depsgraph_get()
    lowest = float("inf")
    for obj in bpy.data.objects:
        if not obj.name.startswith(f"Move {move_index:02d} | ") or obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        transform = evaluated.matrix_world
        lowest = min(lowest, min((transform @ vertex.co).z
                                 for vertex in mesh.vertices))
        evaluated.to_mesh_clear()
    assert -0.015 <= lowest <= 0.06, (
        f"At {second}s, the lowest skin point is {lowest:.3f} m from the floor")

    path = HERE / "mocap" / f"85_{take}.bvh"
    bpy.ops.import_anim.bvh(filepath=str(path), global_scale=0.05,
                            frame_start=1)
    capture = bpy.context.object
    source_frame = 1 + (bvh_frames(path) - 1) * (second - move_start) / duration
    whole = int(source_frame)
    scene.frame_set(whole, subframe=source_frame - whole)
    for side, prefix in (("L", "Left"), ("R", "Right")):
        shoulder, elbow, wrist = joints[side]
        for target, source in (
            (direction(shoulder, elbow), capture.pose.bones[f"{prefix}Arm"]),
            (direction(elbow, wrist), capture.pose.bones[f"{prefix}ForeArm"]),
        ):
            captured = direction(source.head, source.tail)
            angle = degrees(target.angle(captured))
            assert angle < 8, f"At {second}s, {side} arm differs by {angle:.1f} degrees"
    bpy.data.objects.remove(capture, do_unlink=True)
    print(f"POSE_OK {second}s source=85_{take} ground={lowest:.3f}m", flush=True)
