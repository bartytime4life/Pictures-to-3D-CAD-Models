"""Readers for the SVG and PDF exports that share no code with backend.drawing.

They turn a file back into the regions it draws: SVG's endpoint arcs by the conversion
in the SVG specification's implementation notes, PDF's curves as cubic Beziers. Tests
compare those regions with geometry they know by other means.
"""

import math
import re
import xml.etree.ElementTree as ET

import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

SVG = "{http://www.w3.org/2000/svg}"


def svg_arc(start, radius, large, sweep, end, steps=400):
    """Points along an SVG elliptical-arc command with equal radii, by the conversion
    from endpoints to a centre in the SVG specification's implementation notes."""
    (x1, y1), (x2, y2) = start, end
    hx, hy = (x1 - x2) / 2, (y1 - y2) / 2
    radius = max(radius, math.hypot(hx, hy))
    factor = math.sqrt(max(0.0, radius**2 - hx**2 - hy**2) / (hx**2 + hy**2))
    if large == sweep:
        factor = -factor
    cx, cy = factor * hy + (x1 + x2) / 2, -factor * hx + (y1 + y2) / 2
    first = math.atan2(y1 - cy, x1 - cx)
    turn = math.atan2(y2 - cy, x2 - cx) - first
    if sweep == 0 and turn > 0:
        turn -= 2 * math.pi
    elif sweep == 1 and turn < 0:
        turn += 2 * math.pi
    return [
        (cx + radius * math.cos(first + turn * k / steps), cy + radius * math.sin(first + turn * k / steps))
        for k in range(1, steps + 1)
    ]


def svg_path_points(d):
    tokens = d.split()
    points, i = [], 0
    while i < len(tokens):
        command = tokens[i]
        if command in "ML":
            points.append((float(tokens[i + 1]), float(tokens[i + 2])))
            i += 3
        elif command == "A":
            rx, ry, rotation, large, sweep, x, y = (float(t) for t in tokens[i + 1 : i + 8])
            assert rx == ry and rotation == 0
            points.extend(svg_arc(points[-1], rx, int(large), int(sweep), (x, y)))
            i += 8
        else:
            assert command == "Z" and i == len(tokens) - 1, command
            i += 1
    return points


def svg_region(text, around=720 * 4):
    """The region an SVG's shapes enclose, turned upright (y up) in the SVG's own
    millimetres, so that it differs from the model by a translation only; and the
    parsed root."""
    root = ET.fromstring(text)
    rings = {"outline": [], "holes": []}
    for group in root.findall(f"{SVG}g"):
        for shape in group:
            if shape.tag == f"{SVG}circle":
                cx, cy, r = (float(shape.get(k)) for k in ("cx", "cy", "r"))
                points = [
                    (cx + r * math.cos(2 * math.pi * k / around), cy + r * math.sin(2 * math.pi * k / around))
                    for k in range(around)
                ]
            else:
                points = svg_path_points(shape.get("d"))
            rings[group.get("id")].append([(x, -y) for x, y in points])
    outlines = [Polygon(ring) for ring in rings["outline"]]
    holes = [Polygon(ring) for ring in rings["holes"]]
    return unary_union(outlines).difference(unary_union(holes)), root


def pdf_parts(data):
    """A PDF's object table checked against its bytes, its page size in millimetres and
    its page content."""
    assert data.startswith(b"%PDF-1.4\n") and data.endswith(b"%%EOF\n")
    table = int(re.search(rb"startxref\n(\d+)\n%%EOF\n$", data).group(1))
    assert data[table:].startswith(b"xref\n0 7\n0000000000 65535 f \n")
    entries = data[table + len(b"xref\n0 7\n") :].split(b"trailer")[0]
    assert len(entries) == 7 * 20  # each entry is exactly twenty bytes
    for number in range(1, 7):
        offset = int(entries[20 * number : 20 * number + 10])
        assert data[offset:].startswith(b"%d 0 obj\n" % number), number
    assert b"/Root 1 0 R" in data[table:] and b"/Size 7" in data[table:]
    length = int(re.search(rb"/Length (\d+) >>\nstream\n", data).group(1))
    start = data.index(b"stream\n") + len(b"stream\n")
    assert data[start + length :].startswith(b"\nendstream\nendobj\n")
    box_points = re.search(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", data).groups()
    page = tuple(float(v) * 25.4 / 72 for v in box_points)
    return page, data[start : start + length]


def bezier(p0, p1, p2, p3, steps=200):
    out = []
    for k in range(1, steps + 1):
        t = k / steps
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3
        out.append(
            (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])
        )
    return out


def pdf_paths(content):
    """Closed loops, open strokes and text from a page's content, in millimetres."""
    lines = content.decode("cp1252").split("\n")
    scale = lines[0].split()
    assert scale[1:] == ["0", "0", scale[0], "0", "0", "cm"]
    assert float(scale[0]) == pytest.approx(72 / 25.4, abs=1e-6)  # user space is millimetres
    closed, strokes, texts, current = [], [], [], []
    for text in lines[1:]:
        if text.startswith("BT "):
            texts.append(text)
            continue
        tokens = text.split()
        while tokens:
            if tokens[0] == "h":
                closed.append(current)
                current = []
                assert tokens[1] == "S"
                tokens = tokens[2:]
            elif tokens[0] == "S":
                strokes.append(current)
                current = []
                tokens = tokens[1:]
            elif len(tokens) >= 3 and tokens[2] in ("m", "l"):
                assert tokens[2] == "l" or not current
                current.append((float(tokens[0]), float(tokens[1])))
                tokens = tokens[3:]
            elif len(tokens) >= 7 and tokens[6] == "c":
                v = [float(t) for t in tokens[:6]]
                current.extend(bezier(current[-1], v[0:2], v[2:4], v[4:6]))
                tokens = tokens[7:]
            else:
                assert tokens[1] in ("w", "G") or tokens[1:] == ["G", "0", "g"], text
                tokens = []
    assert not current
    return closed, strokes, texts


def length(stroke):
    (ax, ay), (bx, by) = stroke
    return math.hypot(bx - ax, by - ay)
