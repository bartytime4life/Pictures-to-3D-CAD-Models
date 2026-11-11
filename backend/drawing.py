"""Flat drawings of the built profile: an SVG for cutters and vector editors, and a
PDF that prints at 1:1.

Both draw the closed loops the DXF holds. A loop is a list of segments in model
millimetres, y up: ("line", a, b), ("arc", a, m, b) through its midpoint, or one
("circle", centre, radius). Loops come in (layer, loop) pairs, layer "outline" or
"holes". Output depends only on the loops and the name, so a rebuild gives the same
bytes.
"""

import math
from xml.sax.saxutils import escape

from .fitting import arc_geometry

# --- loops --------------------------------------------------------------------------


def fitted_loops(rings):
    """Fitted rings (outer first, as backend.worker.model_rings gives them)."""
    return [("outline" if index == 0 else "holes", ring) for index, ring in enumerate(rings)]


def polygon_loops(polygons):
    """Shapely polygons as loops of straight segments, each part's outline before its holes."""
    loops = []
    for polygon in polygons:
        for layer, ring in [("outline", polygon.exterior), *(("holes", r) for r in polygon.interiors)]:
            points = [(float(x), float(y)) for x, y in list(ring.coords)[:-1]]
            loops.append((layer, [("line", a, b) for a, b in zip(points, points[1:] + points[:1])]))
    return loops


def extent(loops):
    """(xmin, ymin, xmax, ymax) of the drawn curves, arcs included to their bulge."""
    xs, ys = [], []
    for _, loop in loops:
        for segment in loop:
            if segment[0] == "circle":
                (cx, cy), r = segment[1], segment[2]
                xs += [cx - r, cx + r]
                ys += [cy - r, cy + r]
                continue
            for x, y in segment[1:]:
                xs.append(x)
                ys.append(y)
            if segment[0] == "arc":
                (cx, cy), r, start, sweep = arc_geometry(*segment[1:])
                low, high = sorted((start, start + sweep))
                # The arc reaches furthest along an axis where it crosses a quarter turn.
                for quarter in range(math.ceil(low / (math.pi / 2)), math.floor(high / (math.pi / 2)) + 1):
                    angle = quarter * math.pi / 2
                    xs.append(cx + r * math.cos(angle))
                    ys.append(cy + r * math.sin(angle))
    return min(xs), min(ys), max(xs), max(ys)


def _printable(value):
    """Text with every character a file cannot show (controls, lone surrogates,
    non-characters) replaced by a space, so that a name cannot break XML or PDF."""
    return "".join(c if c.isprintable() else " " for c in value)


def _number(value, digits=5):
    """A coordinate in millimetres to 0.01 micrometre, without trailing zeros."""
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


# --- SVG ----------------------------------------------------------------------------

SVG_MARGIN = 1.0  # mm of blank border, so the outline's stroke is not clipped
SVG_STROKE = 0.1  # mm


def svg(loops, name):
    """An SVG whose user unit is one millimetre: lines, true arcs and circles, unfilled.

    The outline and the holes are two groups. SVG's y axis points down, so the drawing
    is flipped to look as the model does from above.
    """
    x0, y0, x1, y1 = extent(loops)
    width, height = x1 - x0 + 2 * SVG_MARGIN, y1 - y0 + 2 * SVG_MARGIN

    def place(point):
        return f"{_number(point[0] - x0 + SVG_MARGIN)} {_number(y1 - point[1] + SVG_MARGIN)}"

    groups = {"outline": [], "holes": []}
    for layer, loop in loops:
        if loop[0][0] == "circle":
            cx, cy = place(loop[0][1]).split()
            groups[layer].append(f'<circle cx="{cx}" cy="{cy}" r="{_number(loop[0][2])}"/>')
            continue
        commands = [f"M {place(loop[0][1])}"]
        for segment in loop:
            if segment[0] == "line":
                commands.append(f"L {place(segment[2])}")
            else:
                (cx, cy), r, start, sweep = arc_geometry(*segment[1:])
                # SVG gives an arc by its end points and radius. Near a half turn the
                # centre that follows from them moves by the square root of any
                # rounding of the ends (0.006 mm for a 4 mm slot end at five decimals),
                # so an arc is written in pieces of at most a third of a turn, which
                # rounding moves by no more than its own size.
                pieces = max(1, math.ceil(abs(sweep) / (2 * math.pi / 3) - 1e-9))
                for index in range(1, pieces + 1):
                    angle = start + sweep * index / pieces
                    end = segment[3] if index == pieces else (cx + r * math.cos(angle), cy + r * math.sin(angle))
                    # A counter-clockwise model arc turns clockwise in SVG's own y-down
                    # frame once flipped, which is sweep-flag 0.
                    commands.append(f"A {_number(r)} {_number(r)} 0 0 {int(sweep < 0)} {place(end)}")
        groups[layer].append(f'<path d="{" ".join(commands)} Z"/>')
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_number(width)}mm" height="{_number(height)}mm"'
            f' viewBox="0 0 {_number(width)} {_number(height)}">'
        ),
        f"<title>{escape(_printable(name))}</title>",
    ]
    for layer, shapes in groups.items():
        lines.append(f'<g id="{layer}" fill="none" stroke="#000" stroke-width="{_number(SVG_STROKE)}">')
        lines.extend(shapes)
        lines.append("</g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


# --- PDF ----------------------------------------------------------------------------

POINTS_PER_MM = 72 / 25.4
# The area A4 (210 x 297) and US Letter (215.9 x 279.4) share. A page this size prints
# at full size on either, and fitting it to the whole sheet of either changes nothing.
# Fitting it to the printable area still shrinks it, which the rulers show.
PAGE = (210.0, 279.4)
MARGIN = 10.0  # blank border, wider than most printers' unprintable edge
HEADER = 12.0  # strip for the title and the printing instruction, at the top
RULER_STRIP = 10.0  # strips for the rulers, at the bottom and the left
RULER = 100.0  # mm; one ruler along each axis, because printers can scale them differently
NAME_LIMIT = 60


def layout(loops):
    """Where everything goes on the page, in millimetres from its bottom-left corner.

    The page is PAGE upright or on its side when the part fits beside the rulers and
    under the header; otherwise it grows to hold the part, and has to be printed on a
    plotter or tiled by the print dialog.
    """
    x0, y0, x1, y1 = extent(loops)
    width, height = x1 - x0, y1 - y0
    used = (2 * MARGIN + RULER_STRIP, 2 * MARGIN + RULER_STRIP + HEADER)
    for page in (PAGE, PAGE[::-1]):
        if width <= page[0] - used[0] + 1e-9 and height <= page[1] - used[1] + 1e-9:
            break
    else:
        base = PAGE if height >= width else PAGE[::-1]
        page = (max(base[0], width + used[0]), max(base[1], height + used[1]))
    left, bottom = MARGIN + RULER_STRIP, MARGIN + RULER_STRIP
    # The part sits in the middle of the area the rulers and header leave free.
    shift = (
        left + (page[0] - MARGIN - left - width) / 2 - x0,
        bottom + (page[1] - MARGIN - HEADER - bottom - height) / 2 - y0,
    )
    return {
        "page": page,
        "shift": shift,
        "size": (width, height),
        "rulers": [
            ((left, MARGIN + 4), (left + RULER, MARGIN + 4)),
            ((MARGIN + 4, bottom), (MARGIN + 4, bottom + RULER)),
        ],
    }


def _text(value):
    """A PDF literal string in the standard Latin encoding; other characters become ?."""
    data = _printable(value).encode("cp1252", errors="replace")
    for special in (b"\\", b"(", b")"):
        data = data.replace(special, b"\\" + special)
    return b"(" + data + b")"


def _arc_curves(centre, radius, start, sweep):
    """Cubic Bezier commands for a circular arc, in steps of at most an eighth of a
    turn; each step lies within 5e-6 of the radius from the true arc."""
    steps = max(1, math.ceil(abs(sweep) / (math.pi / 4) - 1e-9))
    step = sweep / steps
    k = 4 / 3 * math.tan(step / 4) * radius
    out = []
    for index in range(steps):
        a, b = start + index * step, start + (index + 1) * step
        ax, ay = centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)
        bx, by = centre[0] + radius * math.cos(b), centre[1] + radius * math.sin(b)
        out.append(
            " ".join(
                _number(v, 5)
                for v in (ax - k * math.sin(a), ay + k * math.cos(a), bx + k * math.sin(b), by - k * math.cos(b), bx, by)
            )
            + " c"
        )
    return out


def pdf(loops, name):
    """A one-page PDF of the profile at 1:1, with a 100 mm ruler along each axis to
    check the print, and a centre mark in every round hole."""
    plan = layout(loops)
    dx, dy = plan["shift"]

    def place(point):
        return f"{_number(point[0] + dx, 5)} {_number(point[1] + dy, 5)}"

    body = [f"{_number(POINTS_PER_MM, 6)} 0 0 {_number(POINTS_PER_MM, 6)} 0 0 cm", "0 G 0 g", "0.2 w"]
    marks = []
    for _, loop in loops:
        if loop[0][0] == "circle":
            centre, radius = (loop[0][1][0] + dx, loop[0][1][1] + dy), loop[0][2]
            body.append(f"{_number(centre[0] + radius, 5)} {_number(centre[1], 5)} m")
            body.extend(_arc_curves(centre, radius, 0.0, 2 * math.pi))
            body.append("h S")
            arm = min(0.6 * radius, 2.5)
            marks += [
                f"{_number(centre[0] - arm, 5)} {_number(centre[1], 5)} m {_number(centre[0] + arm, 5)} {_number(centre[1], 5)} l S",
                f"{_number(centre[0], 5)} {_number(centre[1] - arm, 5)} m {_number(centre[0], 5)} {_number(centre[1] + arm, 5)} l S",
            ]
            continue
        body.append(f"{place(loop[0][1])} m")
        for segment in loop:
            if segment[0] == "line":
                body.append(f"{place(segment[2])} l")
            else:
                (cx, cy), radius, start, sweep = arc_geometry(*segment[1:])
                body.extend(_arc_curves((cx + dx, cy + dy), radius, start, sweep))
        body.append("h S")
    body.append("0.1 w")
    body.extend(marks)
    for (ax, ay), (bx, by) in plan["rulers"]:
        along = (1, 0) if ay == by else (0, 1)
        body.append(f"{_number(ax)} {_number(ay)} m {_number(bx)} {_number(by)} l S")
        for tick in range(11):
            reach = 3.0 if tick % 5 == 0 else 1.5
            tx, ty = ax + along[0] * 10 * tick, ay + along[1] * 10 * tick
            body.append(
                f"{_number(tx)} {_number(ty)} m {_number(tx + along[1] * reach)} {_number(ty + along[0] * reach)} l S"
            )
    stream = "\n".join(body).encode("ascii")

    def text(size, x, y, value):
        return b"BT /F1 %s Tf %s %s Td " % tuple(_number(v).encode() for v in (size, x, y)) + _text(value) + b" Tj ET"

    width, height = plan["size"]
    shown = name if len(name) <= NAME_LIMIT else name[: NAME_LIMIT - 1] + "…"
    top = plan["page"][1] - MARGIN
    (h_start, _), (v_start, _) = plan["rulers"]
    labels = [
        text(3.5, MARGIN, top - 3.5, f"{shown}: {width:.2f} × {height:.2f} mm, drawn at 1:1"),
        text(
            2.8,
            MARGIN,
            top - 8.5,
            "Print at 100 % (actual size), not fitted to the page. Each ruler must then measure 100 mm.",
        ),
        text(2.5, h_start[0] + RULER + 2, h_start[1] - 0.9, "100 mm"),
        text(2.5, MARGIN, v_start[1] + RULER + 2, "100 mm"),
    ]
    stream += b"\n" + b"\n".join(labels)

    page_points = " ".join(_number(v * POINTS_PER_MM, 3) for v in plan["page"])
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_points}] /Contents 4 0 R"
            " /Resources << /Font << /F1 5 0 R >> >> >>"
        ).encode("ascii"),
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Title " + _text(shown) + b" /Producer (Pictures to CAD) >>",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, content in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + content + b"\nendobj\n"
    table = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, table)
    return bytes(out)
