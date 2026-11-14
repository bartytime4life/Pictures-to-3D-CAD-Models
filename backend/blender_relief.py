"""Rebuild a Pictures to CAD relief or lithophane as an editable Blender scene.

Runs inside Blender (4.2 LTS or later): ``blender --python build_relief.py``, or open
it in the Scripting workspace and press Run Script. It reads ``relief.json`` and
``heightmap.png`` from its own folder and builds:

* ``Relief``: the same closed solid as the workbench's ``model.stl``: a flat base,
  vertical walls, and top vertices (vertex group ``surface``) lifted by a Displace
  modifier that reads the 16-bit height map, one pixel per vertex, without
  interpolation. Strength is the thickness span; it can be edited live.
* A camera and lighting. A lithophane gets a Cycles backlight and a Volume Absorption
  material whose density is the Beer-Lambert coefficient mu (per mm), so a render
  predicts the backlit print.

Optional arguments after ``--``: ``--report FILE`` writes the evaluated mesh's counts,
bounds and volume as JSON; ``--export-stl FILE`` writes the evaluated solid as STL;
``--save FILE`` saves the .blend file.

This file is static: it contains no project values and never downloads anything.
"""

import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np


def here():
    candidates = []
    if "__file__" in globals():
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    space = getattr(bpy.context, "space_data", None)
    text = getattr(space, "text", None) if space else None
    if text is not None and text.filepath:
        candidates.append(os.path.dirname(bpy.path.abspath(text.filepath)))
    candidates.append(os.getcwd())
    for folder in candidates:
        if os.path.isfile(os.path.join(folder, "relief.json")):
            return folder
    raise RuntimeError("relief.json was not found next to build_relief.py. Extract the whole ZIP.")


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    options = {}
    for flag in ("--report", "--export-stl", "--save", "--render"):
        if flag in argv and argv.index(flag) + 1 < len(argv):
            options[flag] = os.path.abspath(argv[argv.index(flag) + 1])
    return options


def clear_default_scene():
    # Remove only Blender's untouched startup objects, never anything the user made.
    for name in ("Cube", "Light", "Camera"):
        item = bpy.data.objects.get(name)
        if item is not None and not item.get("pictures_to_cad"):
            bpy.data.objects.remove(item, do_unlink=True)


def hex_color(value, alpha=1.0):
    value = value.lstrip("#")
    srgb = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*linear, alpha)


def build_mesh(config, levels):
    """Same vertices, diagonals and faces as the workbench's height-field mesher."""
    rows, cols = levels.shape
    px, py = config["pitch_x_mm"], config["pitch_y_mm"]
    t_min, span = config["min_mm"], config["max_mm"] - config["min_mm"]
    z = t_min + levels / 65535.0 * span
    xs = np.arange(cols) * px
    ys = (rows - 1 - np.arange(rows)) * py
    gx, gy = np.meshgrid(xs, ys)
    top = np.column_stack([gx.ravel(), gy.ravel(), np.full(rows * cols, t_min)])
    index = np.arange(rows * cols).reshape(rows, cols)
    a, b = index[:-1, :-1].ravel(), index[:-1, 1:].ravel()
    c, d = index[1:, :-1].ravel(), index[1:, 1:].ravel()
    flat = z.ravel()
    along_ad = np.abs(flat[a] - flat[d]) <= np.abs(flat[b] - flat[c])
    tri_top = np.concatenate(
        [
            np.where(along_ad[:, None], np.column_stack([c, d, a]), np.column_stack([c, d, b])),
            np.where(along_ad[:, None], np.column_stack([d, b, a]), np.column_stack([c, b, a])),
        ]
    )
    ring = np.concatenate([index[-1, :], index[-2::-1, -1], index[0, -2::-1], index[1:-1, 0]])
    count = len(ring)
    base = np.column_stack([top[ring, 0], top[ring, 1], np.zeros(count)])
    centre = np.array([[(xs[0] + xs[-1]) / 2, (ys[0] + ys[-1]) / 2, 0.0]])
    vertices = np.concatenate([top, base, centre])
    start, centre_index = rows * cols, rows * cols + count
    p, q = np.arange(count), (np.arange(count) + 1) % count
    walls = np.concatenate(
        [
            np.column_stack([start + p, start + q, ring[q]]),
            np.column_stack([start + p, ring[q], ring[p]]),
        ]
    )
    floor = np.column_stack([np.full(count, centre_index), start + q, start + p])
    faces = np.concatenate([tri_top, walls, floor])

    mesh = bpy.data.meshes.new(config["name"])
    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    # UVs at pixel centres: vertex (row r, column c) reads pixel (c, rows - 1 - r) of the
    # bottom-up Blender image, i.e. image row r from the top, exactly one pixel each.
    uv = mesh.uv_layers.new(name="heightmap")
    loop_vertices = faces.ravel()
    u = np.zeros(len(vertices))
    v = np.zeros(len(vertices))
    top_index = np.arange(rows * cols)
    u[top_index] = (top_index % cols + 0.5) / cols
    v[top_index] = (rows - 1 - top_index // cols + 0.5) / rows
    uv.data.foreach_set("uv", np.column_stack([u[loop_vertices], v[loop_vertices]]).ravel())
    mesh.update()
    return mesh, rows * cols


def heightmap(config, folder):
    path = os.path.join(folder, config["heightmap"])
    image = bpy.data.images.load(path, check_existing=False)
    image.colorspace_settings.name = "Non-Color"
    cols, rows = image.size
    if (cols, rows) != (config["columns"], config["rows"]):
        raise RuntimeError("heightmap.png does not match relief.json. Extract the ZIP again.")
    pixels = np.empty(cols * rows * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    # Blender stores rows bottom-up; flip to the workbench's top-down row order.
    red = pixels.reshape(rows, cols, 4)[::-1, :, 0]
    return image, np.round(red.astype(np.float64) * 65535)


def relief_object(config, folder):
    image, levels = heightmap(config, folder)
    mesh, top_count = build_mesh(config, levels)
    obj = bpy.data.objects.new("Relief", mesh)
    obj["pictures_to_cad"] = True
    bpy.context.scene.collection.objects.link(obj)
    group = obj.vertex_groups.new(name="surface")
    group.add(list(range(top_count)), 1.0, "REPLACE")
    texture = bpy.data.textures.new("Height map", type="IMAGE")
    texture.image = image
    texture.extension = "EXTEND"
    # Nearest-pixel lookup at pixel centres reads each stored level exactly. Some of these
    # sampling options differ between Blender releases; set the ones this release has.
    for attribute, value in (
        ("use_interpolation", False),
        ("use_mipmap", False),
        ("use_mipmap_gauss", False),
        ("filter_type", "BOX"),
        ("filter_size", 0.1),
    ):
        if hasattr(texture, attribute):
            setattr(texture, attribute, value)
    modifier = obj.modifiers.new("Height", type="DISPLACE")
    modifier.texture = texture
    modifier.texture_coords = "UV"
    modifier.uv_layer = "heightmap"
    modifier.direction = "Z"
    modifier.space = "LOCAL"
    modifier.mid_level = 0.0
    modifier.strength = config["max_mm"] - config["min_mm"]
    modifier.vertex_group = "surface"
    return obj


def material(config, obj):
    mat = bpy.data.materials.new("Relief material")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    output = nodes.get("Material Output")
    shader = nodes.get("Principled BSDF")
    if config["mode"] == "lithophane":
        # Beer-Lambert in Cycles: a clear surface and a black absorber with density mu.
        nodes.remove(shader)
        surface = nodes.new("ShaderNodeBsdfTransparent")
        volume = nodes.new("ShaderNodeVolumeAbsorption")
        volume.inputs["Color"].default_value = (0, 0, 0, 1)
        volume.inputs["Density"].default_value = config["mu_per_mm"]
        links.new(surface.outputs[0], output.inputs["Surface"])
        links.new(volume.outputs[0], output.inputs["Volume"])
    else:
        shader.inputs["Base Color"].default_value = hex_color(config["color"])
        shader.inputs["Roughness"].default_value = 0.55
    obj.data.materials.append(mat)


def staging(config):
    scene = bpy.context.scene
    width, height = config["dimensions_mm"]["width"], config["dimensions_mm"]["height"]
    cx, cy = width / 2, height / 2
    camera_data = bpy.data.cameras.new("Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(width, height) * 1.1
    camera_data.clip_end = 10000
    camera = bpy.data.objects.new("Camera", camera_data)
    camera["pictures_to_cad"] = True
    camera.location = (cx, cy, 500)
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.resolution_x = 1600
    scene.render.resolution_y = max(16, round(1600 * height / width))
    if config["mode"] == "lithophane":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 64
        # Standard view: rendered pixels are the sRGB encoding of transmitted light, with
        # no filmic tone curve, so a render can be compared with the Beer-Lambert map.
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
        # The camera looks down -Z through the part to an emitting panel beneath it.
        panel_mesh = bpy.data.meshes.new("Backlight")
        size = max(width, height) * 1.6
        panel_mesh.from_pydata(
            [
                (cx - size, cy - size, -20),
                (cx + size, cy - size, -20),
                (cx + size, cy + size, -20),
                (cx - size, cy + size, -20),
            ],
            [],
            [(0, 1, 2, 3)],
        )
        panel = bpy.data.objects.new("Backlight", panel_mesh)
        panel["pictures_to_cad"] = True
        glow = bpy.data.materials.new("Backlight")
        glow.use_nodes = True
        nodes = glow.node_tree.nodes
        nodes.remove(nodes.get("Principled BSDF"))
        emission = nodes.new("ShaderNodeEmission")
        emission.inputs["Strength"].default_value = 1.0
        glow.node_tree.links.new(emission.outputs[0], nodes.get("Material Output").inputs[0])
        panel_mesh.materials.append(glow)
        scene.collection.objects.link(panel)
        if scene.world is None:
            scene.world = bpy.data.worlds.new("World")
        scene.world.color = (0, 0, 0)
    else:
        sun_data = bpy.data.lights.new("Raking light", type="SUN")
        sun_data.energy = 4
        sun = bpy.data.objects.new("Raking light", sun_data)
        sun["pictures_to_cad"] = True
        # 25 degrees above the horizon from the upper left: shallow light reveals relief.
        sun.rotation_euler = (math.radians(65), 0, math.radians(-135))
        scene.collection.objects.link(sun)


def evaluated_report(obj, path):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    coordinates = np.array([v.co[:] for v in bm.verts])
    report = {
        "vertices": len(bm.verts),
        "triangles": len(bm.faces),
        "volume_mm3": bm.calc_volume(signed=True),
        "bounds_mm": {
            "min": coordinates.min(axis=0).tolist(),
            "max": coordinates.max(axis=0).tolist(),
        },
        "manifold": all(edge.is_manifold for edge in bm.edges),
        "blender_version": bpy.app.version_string,
    }
    bm.free()
    evaluated.to_mesh_clear()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


def main():
    folder = here()
    with open(os.path.join(folder, "relief.json"), encoding="utf-8") as handle:
        config = json.load(handle)
    if config.get("format") != "pictures-to-cad-blender-relief":
        raise RuntimeError("relief.json is not a Pictures to CAD relief description.")
    clear_default_scene()
    units = bpy.context.scene.unit_settings
    units.system, units.scale_length, units.length_unit = "METRIC", 0.001, "MILLIMETERS"
    obj = relief_object(config, folder)
    material(config, obj)
    staging(config)
    for other in list(bpy.context.scene.objects):
        if other is not None and other != obj:
            other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    options = arguments()
    if "--report" in options:
        evaluated_report(obj, options["--report"])
    if "--export-stl" in options:
        bpy.ops.wm.stl_export(
            filepath=options["--export-stl"],
            export_selected_objects=True,
            apply_modifiers=True,
            ascii_format=False,
        )
    if "--render" in options:
        scene = bpy.context.scene
        scene.render.filepath = options["--render"]
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
    if "--save" in options:
        bpy.ops.wm.save_as_mainfile(filepath=options["--save"])
    print(f"Pictures to CAD: built {config['mode']} '{config['name']}' from {folder}")


main()
