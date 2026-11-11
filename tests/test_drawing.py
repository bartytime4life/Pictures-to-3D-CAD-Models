"""The SVG and the 1:1 PDF must hold the built profile's geometry at true size.

The test part is defined by its design numbers and sampled here directly. The files are
read back by parsers written in this file (SVG's endpoint arcs, PDF's Bezier curves),
which share no code with backend.drawing, and the recovered regions are compared with
the design as areas. A mirrored drawing, a wrong arc flag, a shifted hole or a wrong
scale each leave a region that does not match.
"""

import math
import xml.etree.ElementTree as ET

import pytest
from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient

from backend import drawing
from tests.readers import SVG, bezier, length, pdf_parts, pdf_paths, svg_path_points, svg_region

ANGLE = math.radians(17.0)  # the part is turned, so nothing is aligned with an axis
ROUND = 2880  # points sampled round a circle: an 11 mm one loses 0.0003 mm2 of its area


def turned(point):
    x, y = point
    return (x * math.cos(ANGLE) - y * math.sin(ANGLE), x * math.sin(ANGLE) + y * math.cos(ANGLE))


def on_circle(centre, radius, degrees):
    a = math.radians(degrees)
    return turned((centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)))


def arc(centre, radius, start, end):
    """An arc segment from its design numbers, and 400 points sampled along it."""
    segment = ("arc", *(on_circle(centre, radius, d) for d in (start, (start + end) / 2, end)))
    return segment, [on_circle(centre, radius, start + (end - start) * k / 400) for k in range(400)]


def line(a, b):
    return ("line", turned(a), turned(b)), [turned(a)]


def loop(*pieces):
    return [segment for segment, _ in pieces], [p for _, points in pieces for p in points]


def design():
    """A 120 x 70 plate with R8 corners, turned 17 degrees, with no symmetry: a D22
    bore left of centre and above it, one D6 hole in a corner, and a 24 x 8 slot low on
    the right. Returns its (layer, loop) pairs and the region it encloses."""
    outer, outer_points = loop(
        line((-52, -35), (52, -35)),
        arc((52, -27), 8, -90, 0),
        line((60, -27), (60, 27)),
        arc((52, 27), 8, 0, 90),
        line((52, 35), (-52, 35)),
        arc((-52, 27), 8, 90, 180),
        line((-60, 27), (-60, -27)),
        arc((-52, -27), 8, 180, 270),
    )
    # Traversed clockwise, as a traced hole can be: its arcs sweep the other way.
    slot, slot_points = loop(
        line((33, -8), (17, -8)),
        arc((17, -12), 4, 90, 270),
        line((17, -16), (33, -16)),
        arc((33, -12), 4, -90, 90),
    )
    circles = [((-20, 6), 11.0), ((48, 25), 3.0)]
    loops = [("outline", outer), ("holes", slot)]
    holes = [slot_points]
    for centre, radius in circles:
        loops.append(("holes", [("circle", turned(centre), radius)]))
        holes.append([on_circle(centre, radius, 360 * k / ROUND) for k in range(ROUND)])
    return loops, Polygon(outer_points, holes)


AREA = 120 * 70 - (4 - math.pi) * 64 - (16 * 8 + math.pi * 16) - math.pi * (121 + 9)


def test_the_design_region_has_its_analytic_area():
    _, region = design()
    assert region.is_valid
    assert region.area == pytest.approx(AREA, abs=0.01)


def test_extent_includes_the_bulge_of_arcs_and_circles():
    loops, region = design()
    assert drawing.extent(loops) == pytest.approx(region.bounds, abs=1e-3)
    # An arc's widest point lies between its ends: a half circle from 0 to 180 degrees.
    half = [("outline", [("arc", (5.0, 0.0), (0.0, 5.0), (-5.0, 0.0)), ("line", (-5.0, 0.0), (5.0, 0.0))])]
    assert drawing.extent(half) == pytest.approx((-5, 0, 5, 5))
    assert drawing.extent([("holes", [("circle", (10.0, -2.0), 3.0)])]) == pytest.approx((7, -5, 13, 1))


def test_the_svg_holds_the_design_at_one_unit_per_millimetre():
    loops, region = design()
    # The exact extent (checked against the sampled region above), so that the sampled
    # region's own 1e-5 mm shortfall at each arc's widest point does not shift the map.
    x0, y0, x1, y1 = drawing.extent(loops)
    read, root = svg_region(drawing.svg(loops, "Plate"), ROUND)
    assert read.is_valid
    # Upright, the SVG shows the design moved so that its left and top sit one margin in.
    placed = translate(region, drawing.SVG_MARGIN - x0, -drawing.SVG_MARGIN - y1)
    # The region read back covers the design and nothing else, to within the sampling.
    assert read.symmetric_difference(placed).area < 0.01
    assert read.area == pytest.approx(AREA, abs=0.01)
    width, height = x1 - x0 + 2 * drawing.SVG_MARGIN, y1 - y0 + 2 * drawing.SVG_MARGIN
    assert root.get("width").endswith("mm") and root.get("height").endswith("mm")
    assert float(root.get("width")[:-2]) == pytest.approx(width, abs=1e-5)
    assert float(root.get("height")[:-2]) == pytest.approx(height, abs=1e-5)
    # The view box matches the stated size, so one user unit is one millimetre.
    assert [float(v) for v in root.get("viewBox").split()] == pytest.approx([0, 0, width, height], abs=1e-5)


def test_the_svg_keeps_arcs_and_circles_as_such_in_two_groups():
    loops, _ = design()
    root = ET.fromstring(drawing.svg(loops, "Plate"))
    groups = {g.get("id"): g for g in root.findall(f"{SVG}g")}
    assert list(groups) == ["outline", "holes"]
    assert [len(groups[k]) for k in groups] == [1, 3]
    assert groups["outline"][0].get("d").count(" A ") == 4
    # A half-turn slot end is written as two arcs; see the next test for why.
    assert groups["holes"].find(f"{SVG}path").get("d").count(" A ") == 4
    assert sorted(float(c.get("r")) for c in groups["holes"].findall(f"{SVG}circle")) == [3, 11]
    for group in groups.values():
        assert group.get("fill") == "none" and float(group.get("stroke-width")) == drawing.SVG_STROKE


def test_a_half_turn_arc_survives_the_rounding_of_its_ends():
    # An SVG arc is given by its ends and radius. For a half turn, ends rounded to five
    # decimals can leave the chord 1e-5 mm short of the diameter, and the arc through
    # them then bulges sqrt(r * 1e-5) too far or too little: 0.006 mm for these 4 mm
    # slot ends. A slot turned to any angle but a right one would show it.
    for degrees in (7.0, 17.0, 33.3, 61.0, 118.5):
        a = math.radians(degrees)
        along, across = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))

        def at(u, v, along=along, across=across):
            return (u * along[0] + v * across[0], u * along[1] + v * across[1])

        slot = [
            ("arc", at(8, -4), at(12, 0), at(8, 4)),
            ("line", at(8, 4), at(-8, 4)),
            ("arc", at(-8, 4), at(-12, 0), at(-8, -4)),
            ("line", at(-8, -4), at(8, -4)),
        ]
        root = ET.fromstring(drawing.svg([("outline", slot)], "Slot"))
        points = svg_path_points(root.find(f"{SVG}g")[0].get("d"))
        # SVG's y axis points down, so the slot's own axes are mirrored there.
        lengthwise = [x * along[0] - y * along[1] for x, y in points]
        crosswise = [x * across[0] - y * across[1] for x, y in points]
        assert max(lengthwise) - min(lengthwise) == pytest.approx(24.0, abs=1e-4), degrees
        assert max(crosswise) - min(crosswise) == pytest.approx(8.0, abs=1e-4), degrees


def test_the_pdf_draws_the_design_at_true_size_on_a_page_both_paper_sizes_hold():
    loops, region = design()
    page, content = pdf_parts(drawing.pdf(loops, "Plate"))
    assert page == pytest.approx((210.0, 279.4), abs=1e-3)
    assert page[0] <= 210 + 1e-3 and page[1] <= 279.4 + 1e-3  # inside A4 and inside US Letter
    closed, _, _ = pdf_paths(content)
    rings = sorted(closed, key=lambda ring: -Polygon(ring).area)
    read = orient(Polygon(rings[0], rings[1:]))
    assert read.is_valid and len(rings) == 4
    # The same shape and size as the design, moved but neither turned, mirrored nor scaled.
    dx, dy = drawing.layout(loops)["shift"]
    assert read.symmetric_difference(translate(region, dx, dy)).area < 0.01
    assert read.area == pytest.approx(AREA, abs=0.01)
    # It lies clear of the margins, the rulers' strips and the header.
    free = box(
        drawing.MARGIN + drawing.RULER_STRIP,
        drawing.MARGIN + drawing.RULER_STRIP,
        page[0] - drawing.MARGIN,
        page[1] - drawing.MARGIN - drawing.HEADER,
    )
    assert free.contains(read)
    # And in the middle of that free area.
    assert read.envelope.centroid.coords[0] == pytest.approx(free.centroid.coords[0], abs=1e-3)


def test_the_pdf_has_a_100_mm_ruler_along_each_axis_and_a_mark_in_each_round_hole():
    loops, _ = design()
    plan = drawing.layout(loops)
    _, strokes, texts = pdf_paths(pdf_parts(drawing.pdf(loops, "Plate"))[1])
    assert all(len(stroke) == 2 for stroke in strokes)
    rulers = [s for s in strokes if length(s) > 50]
    assert [length(s) for s in rulers] == pytest.approx([100, 100], abs=1e-9)
    (hx0, hy0), (_, hy1) = rulers[0]
    (vx0, vy0), (vx1, _) = rulers[1]
    assert hy0 == hy1 and vx0 == vx1  # one lies along each axis
    assert [tuple(map(tuple, r)) for r in rulers] == [tuple(r) for r in plan["rulers"]]
    # Both stay in the strips the part is kept out of.
    assert hy0 < drawing.MARGIN + drawing.RULER_STRIP and vx0 < drawing.MARGIN + drawing.RULER_STRIP
    assert min(hx0, hy0, vx0, vy0) >= drawing.MARGIN
    ticks = [s for s in strokes if length(s) in (pytest.approx(1.5), pytest.approx(3.0))]
    assert len(ticks) == 22
    assert sorted(round(s[0][0] - hx0, 6) for s in ticks if s[0][1] == hy0) == [10 * k for k in range(11)]
    assert sorted(round(s[0][1] - vy0, 6) for s in ticks if s[0][0] == vx0) == [10 * k for k in range(11)]
    # A cross through the centre of each round hole, and none in the slot.
    marks = [s for s in strokes if s not in rulers and s not in ticks]
    centres = sorted(
        (round((s[0][0] + s[1][0]) / 2 - plan["shift"][0], 4), round((s[0][1] + s[1][1]) / 2 - plan["shift"][1], 4))
        for s in marks
    )
    expected = sorted(tuple(round(v, 4) for v in turned(c)) for c in ((-20, 6), (48, 25)) for _ in range(2))
    assert centres == expected
    assert sorted(round(length(s), 4) for s in marks) == [3.6, 3.6, 5, 5]  # 0.6 r each way, at most 2.5
    assert sum("(100 mm)" in t for t in texts) == 2
    assert any("Print at 100 %" in t and "must then measure 100 mm" in t for t in texts)


def rectangle(width, height):
    corners = [(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)]
    return [("outline", [("line", a, b) for a, b in zip(corners, corners[1:] + corners[:1])])]


@pytest.mark.parametrize(
    ("size", "page"),
    [
        ((120, 70), (210.0, 279.4)),
        ((180, 237.4), (210.0, 279.4)),  # the largest part the upright page holds
        ((180.5, 100), (279.4, 210.0)),  # too wide upright: the page is turned
        ((249.4, 168), (279.4, 210.0)),  # the largest part the turned page holds
        ((100, 240), (210.0, 282.0)),  # too tall for either: the page grows
        ((400, 300), (430.0, 342.0)),
    ],
)
def test_the_page_turns_or_grows_to_hold_the_part(size, page):
    loops = rectangle(*size)
    plan = drawing.layout(loops)
    assert plan["page"] == pytest.approx(page)
    measured, content = pdf_parts(drawing.pdf(loops, "Plate"))
    assert measured == pytest.approx(page, abs=1e-3)
    (part,), strokes, _ = pdf_paths(content)
    xs, ys = zip(*part)
    assert (max(xs) - min(xs), max(ys) - min(ys)) == pytest.approx(size, abs=1e-4)
    assert min(xs) >= drawing.MARGIN + drawing.RULER_STRIP - 1e-6
    assert min(ys) >= drawing.MARGIN + drawing.RULER_STRIP - 1e-6
    assert max(xs) <= page[0] - drawing.MARGIN + 1e-6
    assert max(ys) <= page[1] - drawing.MARGIN - drawing.HEADER + 1e-6
    # The rulers are still whole and on the page.
    assert [length(s) for s in strokes if length(s) > 50] == pytest.approx([100, 100])
    assert all(0 <= x <= page[0] and 0 <= y <= page[1] for s in strokes for x, y in s)


def test_bezier_arcs_stay_within_a_few_millionths_of_the_radius():
    centre, radius = (3.0, -2.0), 100.0
    for start, sweep in ((0.3, 2 * math.pi), (1.0, -2.2), (-2.0, 0.4), (0.0, math.pi / 4)):
        first = (centre[0] + radius * math.cos(start), centre[1] + radius * math.sin(start))
        points = [first]
        for command in drawing._arc_curves(centre, radius, start, sweep):
            v = [float(t) for t in command.split()[:6]]
            points.extend(bezier(points[-1], v[0:2], v[2:4], v[4:6]))
        worst = max(abs(math.hypot(x - centre[0], y - centre[1]) - radius) for x, y in points)
        assert worst < 5e-6 * radius + 1e-5, (start, sweep, worst)  # 1e-5: five printed decimals
        last = (centre[0] + radius * math.cos(start + sweep), centre[1] + radius * math.sin(start + sweep))
        assert points[-1] == pytest.approx(last, abs=1e-5)


def test_a_name_cannot_break_either_file():
    loops, _ = design()
    name = 'Bracket (v2) \\ <"A&B">\n\té 日本 🙂'
    root = ET.fromstring(drawing.svg(loops, name))
    assert root.find(f"{SVG}title").text == name.replace("\n\t", "  ")
    # Characters XML cannot hold at all become spaces and leave the file well formed.
    hostile = ET.fromstring(drawing.svg(loops, "a\x00b\x0bc\uffffd\ud800e"))
    assert hostile.find(f"{SVG}title").text == "a b c d e"
    assert b"(a b c d e: " in drawing.pdf(loops, "a\x00b\x0bc\uffffd\ud800e")
    data = drawing.pdf(loops, name)
    _, content = pdf_parts(data)
    shown = b'Bracket \\(v2\\) \\\\ <"A&B">  \xe9 ?? ?'
    assert b"Td (" + shown + b": 131.24 \xd7 98.05 mm, drawn at 1:1) Tj ET" in content
    assert b"/Title (" + shown + b") /Producer" in data
    # A long name is cut, so the title stays on the page.
    long = drawing.pdf(loops, "N" * 200)
    assert b"(" + b"N" * 59 + b"\x85: " in long and b"N" * 60 not in long


def test_fitted_rings_put_the_first_on_the_outline_layer_and_the_rest_on_holes():
    rings = [[("circle", (0.0, 0.0), 30.0)], [("circle", (0.0, 0.0), 8.0)], [("circle", (12.0, 0.0), 2.0)]]
    assert drawing.fitted_loops(rings) == [("outline", rings[0]), ("holes", rings[1]), ("holes", rings[2])]
    root = ET.fromstring(drawing.svg(drawing.fitted_loops(rings), "Disc"))
    assert [len(group) for group in root.findall(f"{SVG}g")] == [1, 2]


def test_polygons_become_loops_of_straight_segments():
    square = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], [[(2, 2), (2, 4), (4, 4), (4, 2)]])
    other = Polygon([(12, 0), (20, 0), (20, 10), (12, 10)])
    loops = drawing.polygon_loops([square, other])
    assert [layer for layer, _ in loops] == ["outline", "holes", "outline"]
    assert [len(ring) for _, ring in loops] == [4, 4, 4]
    assert all(segment[0] == "line" for _, ring in loops for segment in ring)
    assert all(a[2] == b[1] for _, ring in loops for a, b in zip(ring, ring[1:] + ring[:1]))  # closed
    root = ET.fromstring(drawing.svg(loops, "Split"))
    outline, holes = root.findall(f"{SVG}g")
    assert len(outline) == 2 and len(holes) == 1
    assert root.get("width") == "22mm" and root.get("height") == "12mm"
    closed, _, _ = pdf_paths(pdf_parts(drawing.pdf(loops, "Split"))[1])
    assert sorted(Polygon(ring).area for ring in closed) == pytest.approx([4, 80, 100])


def test_the_same_input_gives_the_same_bytes():
    loops, _ = design()
    assert drawing.pdf(loops, "Plate") == drawing.pdf(loops, "Plate")
    assert drawing.svg(loops, "Plate") == drawing.svg(loops, "Plate")
