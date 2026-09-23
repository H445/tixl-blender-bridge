"""Run by Blender in the background; never execute in TiXL's render loop.

The saved .blend is the authoring input. This worker writes a disposable
staging cache that the host process validates before publishing.
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tixl_animation_export as exporter


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", type=Path, required=True)
    return parser.parse_args(argv)


def configure(scene, profile, staging):
    exporter.OUT = staging / "worlds"
    exporter.SOURCE_FPS = scene.render.fps / scene.render.fps_base
    exporter.SOURCE_START = float(scene.frame_start)
    duration = (scene.frame_end - scene.frame_start) / exporter.SOURCE_FPS
    exporter.END = max(2, round(duration * exporter.FPS) + 1)
    raw = scene.get("tixl_worlds")
    if raw:
        spec = json.loads(raw) if isinstance(raw, str) else list(raw)
        worlds = {}
        clips = {}
        for entry in spec:
            name = str(entry["name"])
            if not name or name in worlds or "/" in name or "\\" in name:
                raise ValueError(f"Invalid or duplicate TiXL world name: {name!r}")
            worlds[name] = str(entry["collection"])
            start = float(entry.get("start_seconds", 0))
            end = float(entry.get("end_seconds", duration))
            clips[name] = (max(1, round(start * exporter.FPS) + 1),
                           min(exporter.END, round(end * exporter.FPS) + 1))
            if clips[name][0] >= clips[name][1]:
                raise ValueError(f"Empty TiXL world clip: {name}")
        exporter.WORLD_COLLECTIONS = worlds
        exporter.WORLD_CLIPS = clips
    else:
        exporter.WORLD_COLLECTIONS = {"main": scene.collection.name}
        exporter.WORLD_CLIPS = {"main": (1, exporter.END)}


def camera_shots(scene, profile, duration, staging):
    markers = sorted((m for m in scene.timeline_markers if m.camera), key=lambda m: m.frame)
    if not markers:
        if scene.camera is None:
            raise ValueError("The Blender scene has no active camera or camera timeline markers")
        return [(0.0, duration, scene.camera)]
    result = []
    if markers[0].frame > scene.frame_start and scene.camera:
        result.append((0.0, (markers[0].frame - scene.frame_start) / exporter.SOURCE_FPS, scene.camera))
    for index, marker in enumerate(markers):
        start = max(0.0, (marker.frame - scene.frame_start) / exporter.SOURCE_FPS)
        end = (markers[index + 1].frame - scene.frame_start) / exporter.SOURCE_FPS if index + 1 < len(markers) else duration
        if end > start:
            result.append((start, end, marker.camera))
    return result


def write_camera(scene, profile, staging):
    duration = (exporter.END - 1) / exporter.FPS
    shots = camera_shots(scene, profile, duration, staging)
    if not shots or shots[0][0] > 0:
        raise ValueError("Camera coverage does not begin at time zero")
    count = exporter.END - 1
    aspect = (scene.render.resolution_x * scene.render.pixel_aspect_x) / (scene.render.resolution_y * scene.render.pixel_aspect_y)
    output = staging / "camera_60hz.bin"
    with output.open("wb") as stream:
        stream.write(struct.pack("<i", count))
        shot_index = 0
        for i in range(count):
            t = i / exporter.FPS
            while shot_index + 1 < len(shots) and t >= shots[shot_index][1] - 1e-8:
                shot_index += 1
            camera = shots[shot_index][2]
            exporter.set_output_frame(scene, i + 1)
            q = camera.matrix_world.to_quaternion()
            def converted(v): return (float(v.x), float(v.z), -float(v.y))
            values = (*converted(camera.matrix_world.translation),
                      *converted(q @ Vector((0, 0, -1))),
                      *converted(q @ Vector((0, 1, 0))),
                      math.degrees(2 * math.atan(camera.data.sensor_width / (2 * camera.data.lens * aspect))),
                      float(camera.data.clip_start), float(camera.data.clip_end))
            stream.write(struct.pack("<12f", *values))
    (staging / "camera_timeline.json").write_text(json.dumps({
        "shots": [{"id": i + 1, "start": start, "label": camera.name}
                  for i, (start, end, camera) in enumerate(shots)],
        "passages": []
    }, indent=2), encoding="utf-8")
    print(f"CAMERA_COMPLETE {count} samples", flush=True)


def main():
    options = args()
    scene = bpy.context.scene
    options.staging.mkdir(parents=True, exist_ok=True)
    configure(scene, "generic", options.staging)
    exporter.export_all(scene)
    write_camera(scene, "generic", options.staging)
    print("BLEND_SYNC_STAGE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
