"""Procedural 120 BPM nightclub set shared by the full builder and patch script.

The TiXL bridge exports mesh transforms, material emission, and at most eight
lights per world. Keep the room inside those supported channels so the saved
.blend and the TiXL runtime show the same beat-locked design.
"""

import json
from math import cos, pi, sin

import bpy
from mathutils import Vector


BPM = 120
FPS = 60
BEAT = FPS * 60 // BPM  # 30 frames, exactly half a second
PALETTE = ((0.02, 0.82, 1.0), (1.0, 0.035, 0.43), (0.47, 0.19, 1.0),
           (1.0, 0.37, 0.055), (0.1, 1.0, 0.59), (0.9, 0.87, 1.0))


def _mat(name, color, roughness=0.55, metallic=0.0, emission=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    base = tuple(channel * 0.09 for channel in color) if emission else color
    shader.inputs["Base Color"].default_value = (*base, alpha)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Emission Color"].default_value = (*color, 1.0)
    shader.inputs["Emission Strength"].default_value = emission
    shader.inputs["Alpha"].default_value = alpha
    mat.diffuse_color = (*base, alpha)
    if alpha < 1:
        mat.surface_render_method = "DITHERED"
    return mat


def _key_emission(mat, frame, strength):
    socket = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    socket.default_value = strength
    socket.keyframe_insert(data_path="default_value", frame=frame)


def _animate_emission(mat, end, group, floor=False, laser=False):
    for beat in range((end - 1) // BEAT + 1):
        frame = 1 + beat * BEAT
        downbeat = beat % 4 == 0
        phrase = beat % 16 == 0
        if laser:
            high = 2.6 if downbeat else 1.65
            low = 0.8
        elif floor:
            high = 1.3 if downbeat else 0.35
            low = 0.10
        else:
            high = (1.65 if phrase else 1.15 if downbeat else 0.62)
            high *= 1.0 if (beat + group) % 3 else 0.45
            low = 0.07 + group * 0.012
        _key_emission(mat, frame, high)
        if frame + 9 <= end:
            _key_emission(mat, frame + 9, low)


def _mesh_object(name, vertices, faces, materials, face_materials=None):
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    for material in materials:
        mesh.materials.append(material)
    if face_materials:
        for polygon, index in zip(mesh.polygons, face_materials):
            polygon.material_index = index
    return obj


def _box(name, center, size, mat):
    x, y, z = (v / 2 for v in size)
    vertices = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
                (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    obj = _mesh_object(name, vertices, faces, [mat])
    obj.location = center
    return obj


def _cylinder(name, radius, depth, center, mat, sides=64):
    vertices = []
    for z in (-depth / 2, depth / 2):
        vertices.extend((radius * cos(2 * pi * i / sides),
                         radius * sin(2 * pi * i / sides), z) for i in range(sides))
    faces = [tuple(range(sides - 1, -1, -1)), tuple(range(sides, 2 * sides))]
    faces += [(i, (i + 1) % sides, (i + 1) % sides + sides, i + sides)
              for i in range(sides)]
    obj = _mesh_object(name, vertices, faces, [mat])
    obj.location = center
    return obj


def _rings(name, radii, width, z, materials):
    vertices, faces, indices = [], [], []
    sides = 96
    for ring, radius in enumerate(radii):
        offset = len(vertices)
        for r in (radius - width / 2, radius + width / 2):
            vertices.extend((r * cos(2 * pi * i / sides),
                             r * sin(2 * pi * i / sides), z) for i in range(sides))
        for i in range(sides):
            faces.append((offset + i, offset + sides + i,
                          offset + sides + (i + 1) % sides, offset + (i + 1) % sides))
            indices.append(ring % len(materials))
    return _mesh_object(name, vertices, faces, materials, indices)


def _led_wall(materials):
    vertices, faces, indices = [], [], []
    # Separate tiles expose the wall's depth and keep the performer centered.
    columns, rows = 18, 8
    for row in range(rows):
        for column in range(columns):
            cx = (column - (columns - 1) / 2) * 0.45
            cz = 0.85 + row * 0.39
            x0, x1 = cx - 0.195, cx + 0.195
            z0, z1 = cz - 0.155, cz + 0.155
            k = len(vertices)
            vertices.extend(((x0, 4.52, z0), (x1, 4.52, z0),
                             (x1, 4.52, z1), (x0, 4.52, z1)))
            faces.append((k, k + 1, k + 2, k + 3))
            indices.append((column // 3 + row // 2) % len(materials))
    return _mesh_object("Club | 144 beat-reactive LED tiles", vertices, faces,
                        materials, indices)


def _floor_grid(materials):
    vertices, faces, indices = [], [], []
    def quad(points, index):
        k = len(vertices)
        vertices.extend(points)
        faces.append((k, k + 1, k + 2, k + 3))
        indices.append(index)
    for x in (-5.4, -4.5, -3.6, 3.6, 4.5, 5.4):
        quad(((x - 0.013, -4.0, -0.16), (x + 0.013, -4.0, -0.16),
              (x + 0.013, 4.5, -0.16), (x - 0.013, 4.5, -0.16)),
             0 if x < 0 else 1)
    for y in (-3.6, -2.7, 2.7, 3.6, 4.5):
        quad(((-5.5, y - 0.013, -0.16), (5.5, y - 0.013, -0.16),
              (5.5, y + 0.013, -0.16), (-5.5, y + 0.013, -0.16)),
             0 if y < 0 else 1)
    return _mesh_object("Club | perspective floor guides", vertices, faces,
                        materials, indices)


def _beam_mesh(name, mat, top_radius, bottom_radius, sides=10):
    vertices = []
    for z, radius in ((0, top_radius), (1, bottom_radius)):
        vertices.extend((radius * cos(2 * pi * i / sides),
                         radius * sin(2 * pi * i / sides), z) for i in range(sides))
    faces = [(i, (i + 1) % sides, (i + 1) % sides + sides, i + sides)
             for i in range(sides)]
    return _mesh_object(name, vertices, faces, [mat])


def _aim(obj, origin, target, frame):
    direction = Vector(target) - Vector(origin)
    obj.location = origin
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.scale = (1, 1, direction.length)
    for path in ("location", "rotation_quaternion", "scale"):
        obj.keyframe_insert(data_path=path, frame=frame)


def _light(name, location, color, energy, world_collections, set_collection):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = 2.1
    data.color = color
    obj = bpy.data.objects.new(name, data)
    _link(obj, world_collections, set_collection)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 0.9)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def _link(obj, world_collections, set_collection):
    set_collection.objects.link(obj)
    for collection in world_collections:
        collection.objects.link(obj)


def _camera(name, location, target, lens, collection):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_end = 100
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def decorate(scene):
    """Replace the neutral studio with a repeatable club set at the beat grid."""
    if scene.render.fps != FPS or scene.frame_end != 120 * FPS + 1:
        raise ValueError("The nightclub set expects a two-minute, 60 fps source scene")
    spec = json.loads(scene["tixl_worlds"])
    world_collections = [bpy.data.collections[item["collection"]] for item in spec]
    # Objects are shared across world collections so each TiXL GLB contains the
    # same room without duplicating it within a world.
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("Studio |", "Camera |", "Club |", "Laser |", "Projector |")):
            bpy.data.objects.remove(obj, do_unlink=True)
    previous = bpy.data.collections.get("Nightclub | set and beat lighting")
    if previous:
        bpy.data.collections.remove(previous)
    set_collection = bpy.data.collections.new("Nightclub | set and beat lighting")
    scene.collection.children.link(set_collection)
    def add(obj):
        _link(obj, world_collections, set_collection)
        return obj

    charcoal = _mat("Club / charcoal concrete", (0.055, 0.066, 0.092), 0.68)
    stage = _mat("Club / black stage", (0.13, 0.16, 0.22), 0.34, 0.25)
    stage.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.035
    truss = _mat("Club / gunmetal truss", (0.055, 0.07, 0.09), 0.36, 0.67)
    screen = _mat("Club / LED screen backing", (0.008, 0.009, 0.02), 0.8)
    leds = [_mat(f"Club / LED phase {i + 1}", color, 0.48, emission=0.3)
            for i, color in enumerate(PALETTE)]
    for index, material in enumerate(leds):
        _animate_emission(material, scene.frame_end, index)
    floor_glow = [_mat(f"Club / stage ring {i + 1}", PALETTE[i], 0.4, emission=0.2)
                  for i in (0, 2, 1)]
    for index, material in enumerate(floor_glow):
        _animate_emission(material, scene.frame_end, index, floor=True)
    laser_mats = [_mat("Club / laser cyan", PALETTE[0], 0.25, emission=2.7),
                  _mat("Club / laser magenta", PALETTE[1], 0.25, emission=2.7)]
    for index, material in enumerate(laser_mats):
        _animate_emission(material, scene.frame_end, index, laser=True)
    haze = _mat("Club / projector glass haze", (0.08, 0.38, 0.6), 0.6,
                emission=0.06, alpha=0.14)
    projector_rims = (
        _mat("Club / projector rim cyan", PALETTE[0], emission=0.42),
        _mat("Club / projector rim magenta", PALETTE[1], emission=0.42),
    )

    add(_box("Club | dark room floor", (0, 0, -0.27), (14, 13, 0.19), charcoal))
    add(_box("Club | back wall", (0, 4.77, 2.26), (11.7, 0.4, 4.6), charcoal))
    add(_box("Club | left wall", (-5.75, 2.15, 2.25), (0.3, 5.35, 4.5), charcoal))
    add(_box("Club | right wall", (5.75, 2.15, 2.25), (0.3, 5.35, 4.5), charcoal))
    add(_cylinder("Club | raised circular dance floor", 3.4, 0.21,
                  (0, 0, -0.122), stage))
    add(_rings("Club | three concentric beat rings", (2.55, 3.04, 3.38),
               0.055, -0.011, floor_glow))
    add(_floor_grid((leds[0], leds[2])))
    add(_box("Club | LED wall backing", (0, 4.61, 2.23), (8.65, 0.14, 3.66), screen))
    add(_led_wall(leds))
    for x in (-4.35, 4.35):
        add(_box(f"Club | wall truss {x:+.1f}", (x, 4.35, 2.32),
                 (0.12, 0.25, 4.45), truss))
        add(_box(f"Club | side light column {x:+.1f}", (x, 3.82, 2.25),
                 (0.075, 0.075, 3.8), leds[0] if x < 0 else leds[1]))
    for side in (-1, 1):
        for row in range(5):
            add(_box(f"Club | side LED strip {side:+d}-{row + 1}",
                     (side * 5.575, 2.0, 0.82 + row * 0.7),
                     (0.035, 4.55, 0.038), leds[(row + (0 if side < 0 else 2)) % 6]))
    add(_box("Club | overhead truss", (0, 2.4, 4.34), (9.4, 0.16, 0.16), truss))
    add(_box("Club | rear truss", (0, 4.31, 4.35), (9.4, 0.16, 0.16), truss))

    for index in range(8):
        side = -1 if index < 4 else 1
        origin = (side * (2.1 + (index % 4) * 0.46), 2.75, 4.14)
        add(_box(f"Projector | laser head {index + 1:02d}", origin,
                 (0.18, 0.32, 0.2), truss))
        beam = add(_beam_mesh(f"Laser | sweeping ray {index + 1:02d}",
                              laser_mats[index % 2], 0.007, 0.007))
        for beat in range((scene.frame_end - 1) // BEAT + 1):
            phase = 2 * pi * (beat / 16 + index / 8)
            target = (side * 2.2 + 1.15 * sin(phase),
                      4.0 + 0.24 * cos(phase), 0.3 + 0.25 * sin(phase * 0.5))
            _aim(beam, origin, target, 1 + beat * BEAT)

    for index, side in enumerate((-1, 1)):
        origin = (side * 3.15, 1.9, 4.15)
        add(_box(f"Projector | gobo housing {index + 1}", origin,
                 (0.4, 0.42, 0.29), truss))
        cone = add(_beam_mesh(f"Projector | glass haze cone {index + 1}",
                              haze, 0.05, 1.0, sides=20))
        rim_rays = [add(_beam_mesh(f"Projector | beam edge {index + 1}-{edge + 1}",
                                    projector_rims[index], 0.004, 0.004))
                    for edge in range(2)]
        pool = add(_rings(f"Projector | moving floor gobo {index + 1}",
                          (0.26, 0.44), 0.034, -0.004,
                          [leds[0 if index == 0 else 1]]))
        cone.scale = (0.38, 0.38, 1)
        for beat in range((scene.frame_end - 1) // (BEAT * 2) + 1):
            phase = 2 * pi * (beat / 16 + index / 2)
            target = (side * 2.25 + 0.75 * sin(phase), 1.55 + 0.35 * cos(phase), 0.02)
            _aim(cone, origin, target, 1 + beat * BEAT * 2)
            cone.scale.x = cone.scale.y = 0.38
            cone.keyframe_insert(data_path="scale", frame=1 + beat * BEAT * 2)
            for edge, ray in enumerate(rim_rays):
                _aim(ray, origin,
                     (target[0] + (-0.4 if edge == 0 else 0.4), target[1], 0.04),
                     1 + beat * BEAT * 2)
            pool.location = (target[0], target[1], 0)
            pool.keyframe_insert(data_path="location", frame=1 + beat * BEAT * 2)

    light_spec = (
        ("Club | warm face key", (1.9, -2.4, 3.5), (1.0, 0.76, 0.57), 510),
        ("Club | cool face fill", (-2.8, -1.6, 2.9), (0.43, 0.72, 1.0), 300),
        ("Club | cyan rim", (-2.75, 2.6, 3.8), PALETTE[0], 470),
        ("Club | magenta rim", (2.75, 2.6, 3.8), PALETTE[1], 470),
        ("Club | left projector", (-3.1, 1.7, 4.1), PALETTE[2], 260),
        ("Club | right projector", (3.1, 1.7, 4.1), PALETTE[0], 260),
    )
    for index, (name, location, color, energy) in enumerate(light_spec):
        light = _light(name, location, color, energy, world_collections, set_collection)
        for beat in range((scene.frame_end - 1) // BEAT + 1):
            frame = 1 + beat * BEAT
            factor = 1.22 if beat % 4 == 0 else 1.06 if (beat + index) % 2 == 0 else 0.88
            light.data.energy = energy * factor
            light.data.keyframe_insert(data_path="energy", frame=frame)
            if frame + 10 <= scene.frame_end:
                light.data.energy = energy * 0.84
                light.data.keyframe_insert(data_path="energy", frame=frame + 10)

    cameras = (
        _camera("Club | front camera", (2.7, -7.7, 2.68), (0, 0, 1.0), 39,
                set_collection),
        _camera("Club | side camera", (4.65, -5.45, 2.75), (0, 0, 1.0), 42,
                set_collection),
        _camera("Club | elevated camera", (-3.0, -7.1, 4.5), (0, 0, 0.8), 40,
                set_collection),
    )
    scene.camera = cameras[0]
    camera_order = (0, 0, 1, 0, 2, 1, 0, 2, 1, 0)
    for index, marker in enumerate(sorted(scene.timeline_markers, key=lambda m: m.frame)):
        marker.camera = cameras[camera_order[index % len(camera_order)]]
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.012, 0.018, 0.035, 1)
    background.inputs["Strength"].default_value = 0.28
    scene.world.color = (0.012, 0.018, 0.035)
    scene["nightclub_bpm"] = BPM
    scene["nightclub_beat_origin_frame"] = 1
    scene["nightclub_beat_frames"] = BEAT
    scene.frame_set(1)
    print(f"NIGHTCLUB_SET_BUILT worlds={len(world_collections)} beats=240 lights=6", flush=True)
