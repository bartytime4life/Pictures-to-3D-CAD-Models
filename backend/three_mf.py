"""Geometry-only 3MF Core packages, with explicit millimeter units.

This writer uses the public 3MF Core package layout and mesh representation:
https://github.com/3MFConsortium/spec_core
It does not encode slicer settings, filament assignments or machine instructions.
"""

import math
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

CORE_NAMESPACE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
RELATIONSHIPS_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/content-types"
MODEL_CONTENT_TYPE = "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"
MODEL_RELATIONSHIP = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"
MODEL_PATH = "3D/3dmodel.model"


class ThreeMFError(ValueError):
    """A generated mesh cannot be represented as a closed 3MF object."""


def indexed_mesh(mesh):
    """Weld exact face-local duplicates without moving any generated vertex.

    CadQuery tessellation repeats vertices at face boundaries. 3MF represents
    connectivity through indices, so those copies must share one vertex index.
    Each object is processed separately: adjacent split pieces stay separate.
    """
    coordinates, indices = mesh["vertices"], mesh["triangles"]
    if not coordinates or len(coordinates) % 3 or not indices or len(indices) % 3:
        raise ThreeMFError("The generated mesh is incomplete. Rebuild the model.")
    vertices, lookup, remap = [], {}, []
    for offset in range(0, len(coordinates), 3):
        point = tuple(coordinates[offset : offset + 3])
        if any(not math.isfinite(value) for value in point):
            raise ThreeMFError("The generated mesh contains invalid coordinates.")
        if point not in lookup:
            lookup[point] = len(vertices)
            vertices.append(point)
        remap.append(lookup[point])
    triangles, directed_edges = [], Counter()
    for offset in range(0, len(indices), 3):
        original = indices[offset : offset + 3]
        if any(type(index) is not int or not 0 <= index < len(remap) for index in original):
            raise ThreeMFError("The generated mesh has an invalid triangle index.")
        triangle = tuple(remap[index] for index in original)
        if len(set(triangle)) != 3:
            raise ThreeMFError("The generated mesh contains an empty triangle.")
        a, b, c = (vertices[index] for index in triangle)
        cross = (
            (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
            (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
            (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]),
        )
        if not any(cross):
            raise ThreeMFError("The generated mesh contains an empty triangle.")
        triangles.append(triangle)
        for start, end in zip(triangle, (*triangle[1:], triangle[0])):
            directed_edges[start, end] += 1
    if any(
        count != 1 or directed_edges[end, start] != 1
        for (start, end), count in directed_edges.items()
    ):
        raise ThreeMFError("The generated mesh is not a closed, consistently oriented solid.")
    signed_volume = (
        math.fsum(
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
            for triangle in triangles
            for a, b, c in [(vertices[index] for index in triangle)]
        )
        / 6
    )
    if not math.isfinite(signed_volume) or signed_volume <= 0:
        raise ThreeMFError("The generated mesh has no positive outward-facing solid volume.")
    return vertices, triangles


def _xml(element):
    return ET.tostring(element, encoding="utf-8", xml_declaration=True)


def write_3mf(path: Path, objects, *, name="Measured part"):
    """Write independent mesh objects at their supplied coordinates.

    Every build item uses its object's own coordinates with no implicit placement
    or scaling. The caller supplies assembly meshes or normalized individual parts.
    """
    if not objects:
        raise ThreeMFError("The generated model has no parts.")
    model = ET.Element(
        "model",
        {
            "xmlns": CORE_NAMESPACE,
            "unit": "millimeter",
            "{http://www.w3.org/XML/1998/namespace}lang": "en-US",
        },
    )
    ET.SubElement(model, "metadata", {"name": "Title"}).text = name
    ET.SubElement(model, "metadata", {"name": "Application"}).text = "Pictures to CAD"
    resources = ET.SubElement(model, "resources")
    build = ET.SubElement(model, "build")
    for object_id, item in enumerate(objects, start=1):
        vertices, triangles = indexed_mesh(item["mesh"])
        resource = ET.SubElement(
            resources,
            "object",
            {"id": str(object_id), "type": "model", "name": item["name"]},
        )
        mesh = ET.SubElement(resource, "mesh")
        vertex_list = ET.SubElement(mesh, "vertices")
        for vertex in vertices:
            ET.SubElement(
                vertex_list,
                "vertex",
                {axis: format(value, ".17g") for axis, value in zip("xyz", vertex)},
            )
        triangle_list = ET.SubElement(mesh, "triangles")
        for triangle in triangles:
            ET.SubElement(
                triangle_list,
                "triangle",
                {f"v{index}": str(value) for index, value in enumerate(triangle, start=1)},
            )
        ET.SubElement(build, "item", {"objectid": str(object_id)})
    content_types = ET.Element("Types", {"xmlns": CONTENT_TYPES_NAMESPACE})
    ET.SubElement(
        content_types,
        "Default",
        {
            "Extension": "rels",
            "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
        },
    )
    ET.SubElement(
        content_types, "Default", {"Extension": "model", "ContentType": MODEL_CONTENT_TYPE}
    )
    relationships = ET.Element("Relationships", {"xmlns": RELATIONSHIPS_NAMESPACE})
    ET.SubElement(
        relationships,
        "Relationship",
        {"Id": "rel0", "Type": MODEL_RELATIONSHIP, "Target": f"/{MODEL_PATH}"},
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _xml(content_types))
        archive.writestr("_rels/.rels", _xml(relationships))
        archive.writestr(MODEL_PATH, _xml(model))


def write_mesh_3mf(path: Path, vertices, triangles, *, name="Relief", object_name="Relief"):
    """Write one already-indexed, closed mesh (NumPy arrays) as a 3MF Core package.

    Large height fields have hundreds of thousands of vertices, so the model part is
    serialized directly instead of through per-element ElementTree nodes. The package
    layout, namespaces and units match :func:`write_3mf`.
    """
    from xml.sax.saxutils import quoteattr

    import numpy as np

    vertices = np.asarray(vertices, dtype=np.float64)
    triangles = np.asarray(triangles, dtype=np.int64)
    if (
        vertices.ndim != 2
        or vertices.shape[1] != 3
        or triangles.ndim != 2
        or triangles.shape[1] != 3
        or not len(triangles)
        or not np.all(np.isfinite(vertices))
        or triangles.min() < 0
        or triangles.max() >= len(vertices)
    ):
        raise ThreeMFError("The generated mesh is incomplete. Rebuild the model.")
    vertex_xml = "\n".join(
        f'<vertex x="{x:.9g}" y="{y:.9g}" z="{z:.9g}"/>' for x, y, z in vertices.tolist()
    )
    triangle_xml = "\n".join(
        f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in triangles.tolist()
    )
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<model xmlns="{CORE_NAMESPACE}" unit="millimeter" xml:lang="en-US">\n'
        f'<metadata name="Title">{_escape(name)}</metadata>\n'
        '<metadata name="Application">Pictures to CAD</metadata>\n'
        f'<resources><object id="1" type="model" name={quoteattr(object_name)}><mesh>\n'
        f"<vertices>\n{vertex_xml}\n</vertices>\n<triangles>\n{triangle_xml}\n</triangles>\n"
        "</mesh></object></resources>\n"
        '<build><item objectid="1"/></build>\n</model>\n'
    )
    content_types = ET.Element("Types", {"xmlns": CONTENT_TYPES_NAMESPACE})
    ET.SubElement(
        content_types,
        "Default",
        {
            "Extension": "rels",
            "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
        },
    )
    ET.SubElement(
        content_types, "Default", {"Extension": "model", "ContentType": MODEL_CONTENT_TYPE}
    )
    relationships = ET.Element("Relationships", {"xmlns": RELATIONSHIPS_NAMESPACE})
    ET.SubElement(
        relationships,
        "Relationship",
        {"Id": "rel0", "Type": MODEL_RELATIONSHIP, "Target": f"/{MODEL_PATH}"},
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _xml(content_types))
        archive.writestr("_rels/.rels", _xml(relationships))
        archive.writestr(MODEL_PATH, model.encode("utf-8"))


def _escape(text):
    from xml.sax.saxutils import escape

    return escape(text)
