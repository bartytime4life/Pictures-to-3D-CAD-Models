"""Shared vector figures for the reference library.

Each figure is defined once as a list of primitive shapes and rendered two ways:

* ``Figure.to_svg()`` for the HTML library, the Markdown files, and the README;
* ``Figure.draw(canvas, x, y, width)`` for the ReportLab PDF.

Plotted values are computed here from the formulas the handbook states, so a
figure cannot silently disagree with the text. Standard library only; the
ReportLab import happens inside ``draw`` so SVG generation needs no packages.
"""
from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PALETTE = {
    'paper': '#fffefa', 'soft': '#edf3f6', 'soft2': '#e2ebee', 'line': '#c9d6da',
    'ink': '#172b37', 'blue': '#174d68', 'deep': '#0f3347', 'muted': '#566975',
    'accent': '#c77a1f', 'teal': '#2f7d79', 'grey': '#8a969c', 'white': '#ffffff',
    'sky': '#7d98b7', 'steel': '#5a8aa6', 'pale': '#cfe0ea', 'sand': '#f3e3c7',
}
FONTS = {
    'sans': 'DejaVu Sans, Verdana, Segoe UI, Helvetica, Arial, sans-serif',
    'serif': 'Georgia, DejaVu Serif, Times New Roman, serif',
    'mono': 'DejaVu Sans Mono, Menlo, Consolas, monospace',
}
# ReportLab font names; make-pdf.py registers these before drawing.
RL_FONTS = {
    ('sans', False, False): 'Body', ('sans', True, False): 'BodyBold', ('sans', False, True): 'BodyItalic',
    ('serif', False, False): 'Title', ('serif', True, False): 'TitleBold', ('serif', False, True): 'Title',
    ('mono', False, False): 'Mono', ('mono', True, False): 'Mono', ('mono', False, True): 'Mono',
    # DejaVu ships no bold-italic in the registered set; bold carries the emphasis.
    ('sans', True, True): 'BodyBold', ('serif', True, True): 'TitleBold', ('mono', True, True): 'Mono',
}


def num(v: float) -> str:
    """Compact, deterministic number formatting for SVG output."""
    s = f'{v:.2f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


class Figure:
    def __init__(self, name, width, height, title, desc, background='paper', border=True):
        self.name, self.width, self.height = name, width, height
        self.title, self.desc = title, desc
        self.items = []
        if background:
            self.rect(0.5, 0.5, width - 1, height - 1, fill=background,
                      stroke='line' if border else None, rx=14)

    # ---- primitives -------------------------------------------------------
    def _add(self, kind, **a):
        self.items.append((kind, a))
        return self

    def line(self, x1, y1, x2, y2, stroke='ink', width=1.5, dash=None, alpha=1.0):
        return self._add('line', x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, width=width, dash=dash, alpha=alpha)

    def rect(self, x, y, w, h, fill=None, stroke=None, width=1.0, rx=0, dash=None, alpha=1.0):
        return self._add('rect', x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, width=width, rx=rx, dash=dash, alpha=alpha)

    def circle(self, cx, cy, r, fill=None, stroke=None, width=1.0, dash=None, alpha=1.0):
        return self._add('ellipse', cx=cx, cy=cy, rx=r, ry=r, fill=fill, stroke=stroke, width=width, dash=dash, alpha=alpha)

    def ellipse(self, cx, cy, rx, ry, fill=None, stroke=None, width=1.0, dash=None, alpha=1.0):
        return self._add('ellipse', cx=cx, cy=cy, rx=rx, ry=ry, fill=fill, stroke=stroke, width=width, dash=dash, alpha=alpha)

    def polygon(self, pts, fill=None, stroke=None, width=1.0, dash=None, alpha=1.0):
        return self._add('poly', pts=list(pts), closed=True, fill=fill, stroke=stroke, width=width, dash=dash, alpha=alpha)

    def polyline(self, pts, stroke='ink', width=1.5, dash=None, alpha=1.0):
        return self._add('poly', pts=list(pts), closed=False, fill=None, stroke=stroke, width=width, dash=dash, alpha=alpha)

    def text(self, x, y, s, size=14, fill='ink', anchor='start', bold=False, italic=False, family='sans', alpha=1.0):
        return self._add('text', x=x, y=y, s=str(s), size=size, fill=fill, anchor=anchor,
                         bold=bold, italic=italic, family=family, alpha=alpha)

    def arrow(self, x1, y1, x2, y2, stroke='ink', width=1.5, head=9, both=False, dash=None):
        """A line with filled triangular heads (drawn as polygons so SVG and PDF match)."""
        ang = math.atan2(y2 - y1, x2 - x1)
        def tip(x, y, a):
            return [(x, y), (x - head * math.cos(a - 0.4), y - head * math.sin(a - 0.4)),
                    (x - head * math.cos(a + 0.4), y - head * math.sin(a + 0.4))]
        inset = head * 0.8
        sx, sy = (x1 + inset * math.cos(ang), y1 + inset * math.sin(ang)) if both else (x1, y1)
        self.line(sx, sy, x2 - inset * math.cos(ang), y2 - inset * math.sin(ang), stroke=stroke, width=width, dash=dash)
        self.polygon(tip(x2, y2, ang), fill=stroke)
        if both:
            self.polygon(tip(x1, y1, ang + math.pi), fill=stroke)
        return self

    def arc(self, cx, cy, r, start_deg, end_deg, stroke='ink', width=1.5, dash=None, steps=48):
        pts = [(cx + r * math.cos(math.radians(start_deg + (end_deg - start_deg) * i / steps)),
                cy - r * math.sin(math.radians(start_deg + (end_deg - start_deg) * i / steps))) for i in range(steps + 1)]
        return self.polyline(pts, stroke=stroke, width=width, dash=dash)

    def chip(self, x, y, w, label, fill='blue', color='white', size=13, h=28):
        self.rect(x, y, w, h, fill=fill, rx=h / 2)
        return self.text(x + w / 2, y + h / 2 + size * 0.36, label, size=size, fill=color, anchor='middle', bold=True)

    # ---- SVG --------------------------------------------------------------
    @staticmethod
    def _color(token, css):
        if token is None:
            return 'none'
        hexv = PALETTE.get(token, token)
        return f'var(--fig-{token},{hexv})' if css and token in PALETTE else hexv

    def _paint(self, a, css):
        parts = []
        if 'fill' in a:
            parts.append(f'fill:{self._color(a["fill"], css)}')
        if a.get('stroke'):
            parts.append(f'stroke:{self._color(a["stroke"], css)};stroke-width:{num(a["width"])}')
            parts.append('stroke-linecap:round;stroke-linejoin:round')
            if a.get('dash'):
                parts.append('stroke-dasharray:' + ' '.join(num(d) for d in a['dash']))
        if a.get('alpha', 1.0) != 1.0:
            parts.append(f'opacity:{num(a["alpha"])}')
        return ';'.join(parts)

    def to_svg(self, css_vars=False, inline=False):
        out = []
        size = '' if inline else f' width="{self.width}" height="{self.height}"'
        out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}"{size} '
                   f'role="img" aria-labelledby="{self.name}-title {self.name}-desc" class="figure-svg">')
        out.append(f'<title id="{self.name}-title">{escape(self.title)}</title>')
        out.append(f'<desc id="{self.name}-desc">{escape(self.desc)}</desc>')
        for kind, a in self.items:
            style = self._paint(a, css_vars)
            if kind == 'line':
                out.append(f'<line x1="{num(a["x1"])}" y1="{num(a["y1"])}" x2="{num(a["x2"])}" y2="{num(a["y2"])}" style="{style}"/>')
            elif kind == 'rect':
                rx = f' rx="{num(a["rx"])}"' if a['rx'] else ''
                out.append(f'<rect x="{num(a["x"])}" y="{num(a["y"])}" width="{num(a["w"])}" height="{num(a["h"])}"{rx} style="{style}"/>')
            elif kind == 'ellipse':
                out.append(f'<ellipse cx="{num(a["cx"])}" cy="{num(a["cy"])}" rx="{num(a["rx"])}" ry="{num(a["ry"])}" style="{style}"/>')
            elif kind == 'poly':
                tag = 'polygon' if a['closed'] else 'polyline'
                pts = ' '.join(f'{num(x)},{num(y)}' for x, y in a['pts'])
                out.append(f'<{tag} points="{pts}" style="{style}"/>')
            elif kind == 'text':
                anchor = {'start': 'start', 'middle': 'middle', 'end': 'end'}[a['anchor']]
                weight = ' font-weight="700"' if a['bold'] else ''
                italic = ' font-style="italic"' if a['italic'] else ''
                opacity = f';opacity:{num(a["alpha"])}' if a['alpha'] != 1.0 else ''
                out.append(f'<text x="{num(a["x"])}" y="{num(a["y"])}" font-family="{FONTS[a["family"]]}" '
                           f'font-size="{num(a["size"])}"{weight}{italic} text-anchor="{anchor}" '
                           f'style="fill:{self._color(a["fill"], css_vars)}{opacity}">{escape(a["s"])}</text>')
        out.append('</svg>')
        return '\n'.join(out) + '\n'

    # ---- ReportLab --------------------------------------------------------
    def draw(self, canv, x, y, width):
        """Draw into a ReportLab canvas with the figure's bottom-left corner at (x, y)."""
        from reportlab.lib.colors import HexColor
        s = width / self.width
        H = self.height
        col = lambda t: HexColor(PALETTE.get(t, t))
        canv.saveState()
        canv.translate(x, y)
        canv.scale(s, s)
        canv.setLineCap(1)
        canv.setLineJoin(1)
        for kind, a in self.items:
            canv.saveState()
            fill, stroke = a.get('fill'), a.get('stroke')
            if fill:
                canv.setFillColor(col(fill))
            if stroke:
                canv.setStrokeColor(col(stroke))
                canv.setLineWidth(a['width'])
                canv.setDash(list(a['dash'])) if a.get('dash') else canv.setDash()
            if a.get('alpha', 1.0) != 1.0:
                canv.setFillAlpha(a['alpha'])
                canv.setStrokeAlpha(a['alpha'])
            f, st = (1 if fill else 0), (1 if stroke else 0)
            if kind == 'line':
                canv.line(a['x1'], H - a['y1'], a['x2'], H - a['y2'])
            elif kind == 'rect':
                if a['rx']:
                    canv.roundRect(a['x'], H - a['y'] - a['h'], a['w'], a['h'], a['rx'], fill=f, stroke=st)
                else:
                    canv.rect(a['x'], H - a['y'] - a['h'], a['w'], a['h'], fill=f, stroke=st)
            elif kind == 'ellipse':
                canv.ellipse(a['cx'] - a['rx'], H - a['cy'] - a['ry'], a['cx'] + a['rx'], H - a['cy'] + a['ry'], fill=f, stroke=st)
            elif kind == 'poly':
                p = canv.beginPath()
                (x0, y0), rest = a['pts'][0], a['pts'][1:]
                p.moveTo(x0, H - y0)
                for px, py in rest:
                    p.lineTo(px, H - py)
                if a['closed']:
                    p.close()
                canv.drawPath(p, fill=f, stroke=st)
            elif kind == 'text':
                canv.setFillColor(col(a['fill']))
                canv.setFont(RL_FONTS[(a['family'], a['bold'], a['italic'])], a['size'])
                draw = {'start': canv.drawString, 'middle': canv.drawCentredString, 'end': canv.drawRightString}[a['anchor']]
                draw(a['x'], H - a['y'], a['s'])
            canv.restoreState()
        canv.restoreState()


# ---- shared maths ---------------------------------------------------------

def solve(a, b):
    """Gaussian elimination with partial pivoting (small dense systems)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(c + 1, n):
            k = m[r][c] / m[c][c]
            for j in range(c, n + 1):
                m[r][j] -= k * m[c][j]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][j] * x[j] for j in range(r + 1, n))) / m[r][r]
    return x


def homography4(src, dst):
    """Exact homography from four point pairs (h33 = 1)."""
    a, b = [], []
    for (u, v), (x, y) in zip(src, dst):
        a.append([u, v, 1, 0, 0, 0, -u * x, -v * x]); b.append(x)
        a.append([0, 0, 0, u, v, 1, -u * y, -v * y]); b.append(y)
    h = solve(a, b) + [1.0]
    return [h[0:3], h[3:6], h[6:9]]


def apply_h(H, u, v):
    w = H[2][0] * u + H[2][1] * v + H[2][2]
    return ((H[0][0] * u + H[0][1] * v + H[0][2]) / w, (H[1][0] * u + H[1][1] * v + H[1][2]) / w)


def sagitta(radius, n):
    return radius * (1 - math.cos(math.pi / n))


def load_sources():
    return json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))


def load_routes():
    return json.loads((ROOT / 'assets/data/routes.json').read_text(encoding='utf-8'))


STRENGTH = {'page': 'strong', 'page-http-gzip-decoded': 'strong', 'repository-content': 'strong',
            'search-content': 'medium', 'repository-metadata': 'medium',
            'abstract': 'limited', 'discovery-abstract': 'limited', 'metadata': 'limited'}


# ---- figures ----------------------------------------------------------------

def process_flow():
    f = Figure('process-flow', 1000, 170, 'Five-stage workflow from photographs to a checked print',
               'Capture, measure, reconstruct, model and draw, then print and check; the check feeds back into measurement.')
    steps = [('01', 'Capture', 'photos + scale refs'), ('02', 'Measure', 'datums, calipers'),
             ('03', 'Reconstruct', 'rectify, trace, SfM'), ('04', 'Model & draw', 'CAD + drawings'),
             ('05', 'Print & check', 'coupons, inspection')]
    for i, (n, title, sub) in enumerate(steps):
        x = 20 + i * 198
        last = i == len(steps) - 1
        f.rect(x, 18, 168, 92, fill='blue' if last else 'soft', stroke=None if last else 'line', rx=10)
        f.text(x + 16, 42, n, size=12, fill='accent', bold=True, family='mono')
        f.text(x + 16, 70, title, size=18, fill='white' if last else 'ink', bold=True)
        f.text(x + 16, 94, sub, size=12, fill='pale' if last else 'muted')
        if not last:
            f.arrow(x + 172, 64, x + 194, 64, stroke='sky', width=2, head=8)
    f.polyline([(896, 112), (896, 142), (302, 142), (302, 120)], stroke='accent', width=1.8, dash=(6, 5))
    f.polygon([(302, 112), (296.5, 123), (307.5, 123)], fill='accent')
    f.rect(430, 131, 340, 22, fill='paper')
    f.text(600, 147, 'measure the print · change one variable at a time', size=12.5, fill='accent', anchor='middle')
    return f


def evidence_ladder():
    f = Figure('evidence-ladder', 1000, 300, 'Four evidence classes for every recovered dimension',
               'Measured, image-derived, inferred and unknown, from strongest to weakest. A derived value inherits the weakest class among its inputs.')
    rows = [('Measured', 'instrument or verified', 'drawing', 'blue'),
            ('Image-derived', 'image + stated scale', 'and assumptions', 'teal'),
            ('Inferred', 'symmetry, standards,', 'likely intent', 'accent'),
            ('Unknown', 'no support yet:', 'needs evidence', 'grey')]
    for i, (name, l1, l2, color) in enumerate(rows):
        x, top = 20 + i * 242, 26 + i * 28
        f.rect(x, top, 230, 200 - top, fill=color, rx=8)
        f.text(x + 16, top + 32, f'{i + 1}  {name}', size=20, fill='white', bold=True)
        f.text(x + 16, top + 56, l1, size=13.5, fill='white')
        f.text(x + 16, top + 74, l2, size=13.5, fill='white')
    f.arrow(24, 222, 976, 222, stroke='muted', width=1.4, head=8)
    f.text(24, 242, 'stronger evidence', size=12, fill='muted')
    f.text(976, 242, 'weaker evidence', size=12, fill='muted', anchor='end')
    f.text(24, 279, 'Weakest input wins:', size=15, fill='ink', bold=True)
    f.chip(200, 260, 205, 'image-derived position', fill='teal')
    f.text(422, 280, '+', size=20, fill='ink', anchor='middle', bold=True)
    f.chip(440, 260, 150, 'assumed depth', fill='accent')
    f.text(607, 280, '=', size=20, fill='ink', anchor='middle', bold=True)
    f.chip(625, 260, 175, 'inferred 3D length', fill='accent')
    return f


def chord_error():
    R_mm, e_mm = 10.0, 0.02
    n_min = math.ceil(math.pi / math.acos(1 - e_mm / R_mm))
    f = Figure('chord-error', 1000, 400, 'Chordal (sagitta) error of a tessellated circle',
               f'A circle drawn as n chords deviates by e = R(1 - cos(pi/n)). For R = 10 mm and e = 0.02 mm at least {n_min} segments are needed.')
    cx, cy, r = 215, 200, 160
    f.circle(cx, cy, r, stroke='line', width=1.5, dash=(5, 5))
    hexagon = [(cx + r * math.cos(math.radians(30 + 60 * k)), cy - r * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    f.polygon(hexagon, fill='soft', stroke='blue', width=2)
    a, b = hexagon[0], hexagon[5]
    f.line(a[0], a[1], b[0], b[1], stroke='accent', width=3.5)
    f.arc(cx, cy, r, -30, 30, stroke='accent', width=2.5)
    mid = (cx + r * math.cos(math.radians(30)), cy)
    f.line(mid[0], cy, cx + r, cy, stroke='accent', width=3)
    f.text(cx + r + 10, cy + 5, 'e', size=20, fill='accent', bold=True, italic=True)
    f.line(cx, cy, a[0], a[1], stroke='ink', width=1.4)
    f.line(cx, cy, cx + r, cy, stroke='ink', width=1, dash=(3, 4))
    f.text(cx + 52, cy - 52, 'R', size=18, fill='ink', italic=True, bold=True)
    f.arc(cx, cy, 46, 0, 30, stroke='muted', width=1.4)
    f.text(cx + 54, cy - 10, 'π/n', size=13.5, fill='muted')
    f.circle(cx, cy, 3.5, fill='ink')
    f.text(cx, 388, 'n = 6 shown; the error is exaggerated', size=12, fill='muted', anchor='middle')
    # Right: computed curve of e(n) for R = 10 mm on a log scale.
    x0, x1, y0, y1 = 520, 960, 128, 338
    f.text(470, 40, f'Sagitta error vs. segment count (R = {R_mm:g} mm)', size=16, fill='ink', bold=True)
    f.text(470, 68, 'e = R · (1 − cos(π / n))', size=15, fill='blue', family='mono')
    f.text(470, 92, f'n ≥ π / acos(1 − e/R)  →  e = {e_mm:g} mm needs n = {n_min}', size=13, fill='blue', family='mono')
    X = lambda n: x0 + (n - 10) / 90 * (x1 - x0)
    Y = lambda e: y1 - (math.log10(e) + 3) / 3 * (y1 - y0)
    for e, lab in [(1, '1'), (0.1, '0.1'), (0.01, '0.01'), (0.001, '0.001')]:
        f.line(x0, Y(e), x1, Y(e), stroke='soft2', width=1)
        f.text(x0 - 8, Y(e) + 4, lab, size=11.5, fill='muted', anchor='end')
    for n in (10, 25, 50, 75, 100):
        f.line(X(n), y1, X(n), y1 + 5, stroke='muted', width=1)
        f.text(X(n), y1 + 20, str(n), size=11.5, fill='muted', anchor='middle')
    f.line(x0, y0, x0, y1, stroke='muted', width=1)
    f.line(x0, y1, x1, y1, stroke='muted', width=1)
    f.polyline([(X(n), Y(sagitta(R_mm, n))) for n in range(10, 101)], stroke='blue', width=2.5)
    f.line(x0, Y(e_mm), x1, Y(e_mm), stroke='accent', width=1.5, dash=(6, 4))
    f.text(x1, Y(e_mm) - 8, f'allowed e = {e_mm:g} mm', size=12, fill='accent', anchor='end')
    f.line(X(n_min), Y(sagitta(R_mm, n_min)), X(n_min), y1, stroke='accent', width=1, dash=(2, 3))
    f.circle(X(n_min), Y(sagitta(R_mm, n_min)), 5.5, fill='accent', stroke='paper', width=2)
    f.text(X(n_min) - 12, Y(sagitta(R_mm, n_min)) + 30, f'n = {n_min}: e = {sagitta(R_mm, n_min):.4f} mm', size=12.5, fill='ink', bold=True, anchor='end')
    f.text(x0, y0 - 10, 'e (mm, log scale)', size=11.5, fill='muted')
    f.text((x0 + x1) / 2, 384, 'segments around the circle, n', size=12, fill='muted', anchor='middle')
    return f


def off_plane_depth():
    Z, D, S = 500.0, 60.0, 40.0
    factor = (Z + D) / Z
    f = Figure('off-plane-depth', 1000, 360, 'Depth correction for a feature behind the reference plane',
               f'Under a pinhole model a feature at distance Z + delta appears smaller than its true size at the reference scale; actual = size at reference scale x (Z + delta)/Z. Example: Z = {Z:g} mm, delta = {D:g} mm, factor {factor:.2f}.')
    ay, cxp = 230, 122
    f.rect(58, 208, 52, 44, fill='ink', rx=6)
    f.polygon([(110, 218), (cxp, ay), (110, 242)], fill='ink')
    f.text(84, 274, 'camera', size=12.5, fill='muted', anchor='middle')
    f.line(cxp, ay, 900, ay, stroke='muted', width=1, dash=(4, 5))
    xr, xf, top = 480, 660, 98
    f.line(xr, 62, xr, 300, stroke='blue', width=2)
    f.line(xf, 62, xf, 300, stroke='teal', width=2, dash=(7, 5))
    f.text(xr, 50, 'reference plane', size=13, fill='blue', anchor='middle', bold=True)
    f.text(xf, 50, 'feature plane', size=13, fill='teal', anchor='middle', bold=True)
    yr = ay - (ay - top) * (xr - cxp) / (xf - cxp)
    f.line(cxp, ay, xf, top, stroke='accent', width=1.6, dash=(6, 4))
    f.line(xf, ay, xf, top, stroke='teal', width=9)
    f.line(xr, ay, xr, yr, stroke='blue', width=9)
    f.text(xr - 14, yr + 18, 'size at', size=12.5, fill='blue', anchor='end')
    f.text(xr - 14, yr + 34, 'reference scale', size=12.5, fill='blue', anchor='end')
    f.text(xf + 14, top + 14, 'actual size', size=12.5, fill='teal')
    f.arrow(cxp, 318, xr, 318, stroke='ink', width=1.2, head=7, both=True)
    f.arrow(xr, 318, xf, 318, stroke='ink', width=1.2, head=7, both=True)
    f.rect((cxp + xr) / 2 - 14, 306, 28, 22, fill='paper')
    f.text((cxp + xr) / 2, 323, 'Z', size=15, fill='ink', anchor='middle', italic=True, bold=True)
    f.rect((xr + xf) / 2 - 14, 306, 28, 22, fill='paper')
    f.text((xr + xf) / 2, 323, 'Δ', size=15, fill='ink', anchor='middle', bold=True)
    f.rect(700, 128, 278, 140, fill='soft', rx=10)
    f.text(716, 156, 'actual ≈ size at reference scale', size=13, fill='ink', family='mono')
    f.text(788, 176, '× (Z + Δ) / Z', size=13, fill='ink', family='mono')
    f.text(716, 210, f'Z = {Z:g} mm, Δ = {D:g} mm', size=13, fill='blue')
    f.text(716, 230, f'factor = {Z + D:g} / {Z:g} = {factor:.2f}', size=13, fill='blue')
    f.text(716, 250, f'{S:.1f} mm  →  {S * factor:.1f} mm', size=13, fill='blue', bold=True)
    f.text(20, 350, 'Schematic, not to scale. Features behind the plane (Δ > 0) are larger than the reference scale suggests.',
           size=12, fill='muted')
    return f


def homography():
    f = Figure('homography', 1000, 392, 'Planar rectification with a homography',
               'Four or more point pairs map a tilted rectangle in the image to its known 50 x 90 mm shape. Four pairs fit exactly, so their residuals are zero by construction.')
    quad = [(150, 96), (330, 82), (392, 318), (82, 300)]
    W, Hh = 133.3, 240.0
    rx, ry = 703, 70
    rect = [(rx, ry), (rx + W, ry), (rx + W, ry + Hh), (rx, ry + Hh)]
    Hm = homography4([(0, 0), (1, 0), (1, 1), (0, 1)], quad)
    f.polygon(quad, fill='soft', stroke='blue', width=2)
    for k in range(1, 5):
        u = k / 5
        f.line(*apply_h(Hm, u, 0), *apply_h(Hm, u, 1), stroke='sky', width=1)
    for k in range(1, 9):
        v = k / 9
        f.line(*apply_h(Hm, 0, v), *apply_h(Hm, 1, v), stroke='sky', width=1)
    f.rect(rx, ry, W, Hh, fill='soft', stroke='blue', width=2)
    for k in range(1, 5):
        f.line(rx + W * k / 5, ry, rx + W * k / 5, ry + Hh, stroke='sky', width=1)
    for k in range(1, 9):
        f.line(rx, ry + Hh * k / 9, rx + W, ry + Hh * k / 9, stroke='sky', width=1)
    for i, ((qx, qy), (px, py)) in enumerate(zip(quad, rect), 1):
        for x, y in ((qx, qy), (px, py)):
            f.circle(x, y, 11, fill='accent', stroke='paper', width=2)
            f.text(x, y + 4.5, str(i), size=12, fill='white', anchor='middle', bold=True)
    f.text(236, 50, 'image (pixels)', size=13.5, fill='muted', anchor='middle', bold=True)
    f.text(rx + W / 2, 46, 'rectified plane (mm)', size=13.5, fill='muted', anchor='middle', bold=True)
    f.text(rx + W / 2, ry + Hh + 26, '50 mm', size=13, fill='ink', anchor='middle')
    f.text(rx + W + 16, ry + Hh / 2 + 4, '90 mm', size=13, fill='ink')
    f.arrow(452, 200, 640, 200, stroke='blue', width=2.5, head=11)
    f.text(546, 184, 'H', size=24, fill='blue', anchor='middle', bold=True, italic=True, family='serif')
    f.text(546, 226, '≥ 4 point pairs', size=13, fill='blue', anchor='middle')
    f.text(20, 362, 'Four pairs fit exactly, so their residuals are zero by construction, not evidence of accuracy.', size=12.5, fill='muted')
    f.text(20, 381, 'Use more well-spread points, check residuals, and keep an independent check length.', size=12.5, fill='muted')
    return f


def clearance():
    f = Figure('clearance', 1000, 330, 'Diametral and radial clearance, with an exploratory coupon',
               'Diametral clearance is hole diameter minus shaft diameter; radial clearance is half of it. A coupon of holes tests a range of differences.')
    cx, cy = 200, 168
    f.rect(52, 36, 296, 264, fill='soft2', stroke='line', rx=8)
    f.circle(cx, cy, 110, fill='paper', stroke='blue', width=2)
    f.circle(cx, cy, 86, fill='steel')
    f.text(cx, cy - 4, 'shaft', size=15, fill='white', anchor='middle', bold=True)
    f.text(cx, cy + 16, 'd', size=16, fill='white', anchor='middle', italic=True, bold=True)
    f.text(cx, 72, 'hole D', size=13, fill='blue', anchor='middle', bold=True)
    f.arrow(cx + 86, cy, cx + 110, cy, stroke='accent', width=2, head=6, both=True)
    f.text(cx + 98, cy - 12, 'c', size=16, fill='accent', anchor='middle', bold=True, italic=True)
    f.text(400, 62, 'diametral clearance = D − d', size=16, fill='ink', bold=True, family='mono')
    f.text(400, 90, 'radial clearance c = (D − d) / 2', size=16, fill='ink', family='mono')
    f.text(400, 118, 'Record which definition a coupon uses; clearance and', size=13, fill='muted')
    f.text(400, 136, 'process compensation are separate decisions.', size=13, fill='muted')
    f.text(400, 178, 'Exploratory coupon: diametral differences (example settings, not recommended fits)', size=12, fill='muted')
    f.rect(400, 190, 570, 104, fill='soft2', stroke='line', rx=8)
    for i, c in enumerate((0.10, 0.20, 0.30, 0.40, 0.50)):
        x = 457 + i * 114
        f.circle(x, 232, 22 + (i + 1) * 2.4, fill='paper', stroke='blue', width=1.6)
        f.circle(x, 232, 22, fill='steel', alpha=0.85)
        f.text(x, 282, f'+{c:.2f}', size=13, fill='ink', anchor='middle', family='mono', bold=True)
    return f


def route_map():
    routes = load_routes()
    inputs = routes['inputs']
    wf = routes['workflows']
    order = ['A', 'B', 'C', 'D', 'G', 'V', 'E', 'H']
    top, step = 70, 52
    h = top + step * len(order) + 64
    f = Figure('route-map', 1000, h, 'Route map: from available input to a handbook workflow',
               'Each kind of input leads to a starting workflow. Two goals redirect: an organic subject with an exact mount leads to Workflow E, and a holder for an owned object leads to the held-object section.')
    f.text(30, 40, 'WHAT YOU HAVE', size=12.5, fill='muted', bold=True)
    f.text(970, 40, 'WHERE TO START', size=12.5, fill='muted', bold=True, anchor='end')
    in_y = {}
    gap = (step * len(order) - 8) / len(inputs)
    for i, item in enumerate(inputs):
        y = top + i * gap
        in_y[item['id']] = y + 20
        f.rect(30, y, 380, 40, fill='soft', stroke='line', rx=8)
        f.text(46, y + 25, item['label'], size=13.5, fill='ink')
    wf_y = {}
    for i, key in enumerate(order):
        y = top + i * step
        wf_y[key] = y + 20
        goal_driven = key in ('E', 'H')
        f.rect(600, y, 370, 40, fill='paper' if goal_driven else 'blue', stroke='accent' if goal_driven else None,
               width=2, rx=8, dash=(6, 4) if goal_driven else None)
        f.text(616, y + 25, key if len(key) == 1 else key, size=14, fill='accent' if goal_driven else 'pale', bold=True, family='mono')
        label = f"{wf[key]['short']}  ·  §{wf[key]['section']}"
        f.text(640, y + 25, label, size=14, fill='ink' if goal_driven else 'white', bold=True)
    for item in inputs:
        key = routes['by_input'][item['id']]['workflow']
        y1, y2 = in_y[item['id']], wf_y[key]
        f.polyline([(410, y1), (450, y1), (550, y2), (600, y2)], stroke='sky', width=2)
        f.circle(410, y1, 4, fill='sky')
    for key, goal in (('E', 'mount'), ('H', 'holder')):
        f.text(956, wf_y[key] + 5, f'goal: {goal}', size=11.5, fill='accent', anchor='end', italic=True)
    f.text(30, h - 24, 'Goals refine the route: photo sets that must become editable CAD continue into Workflow D; see the Toolkit route finder.',
           size=12, fill='muted')
    return f


def catalog_composition():
    sources = load_sources()
    cats = {}
    for s in sources:
        c = cats.setdefault(s['category'], {'strong': 0, 'medium': 0, 'limited': 0})
        c[STRENGTH[s['evidence']]] += 1
    rows = sorted(cats.items(), key=lambda kv: (-sum(kv[1].values()), kv[0]))
    biggest = max(sum(v.values()) for _, v in rows)
    top, step = 92, 34
    h = top + step * len(rows) + 30
    f = Figure('catalog-composition', 1000, h, f'{len(sources)} catalog sources by topic and review depth',
               'Horizontal stacked bars: number of sources in each topic, split by how deeply each source was reviewed.')
    f.text(30, 42, f'{len(sources)} sources by topic and review depth', size=18, fill='ink', bold=True, family='serif')
    legend = [('strong', 'blue', 'page or document read'), ('medium', 'teal', 'search index or repository metadata'),
              ('limited', 'accent', 'abstract or bibliographic record')]
    lx = 30
    for key, color, label in legend:
        f.rect(lx, 58, 14, 14, fill=color, rx=3)
        f.text(lx + 20, 70, label, size=12, fill='muted')
        lx += 36 + len(label) * 6.9
    x0, scale = 262, 640 / biggest
    for i, (cat, v) in enumerate(rows):
        y = top + i * step
        f.text(x0 - 12, y + 18, cat, size=13.5, fill='ink', anchor='end')
        x = x0
        for key, color, _ in legend:
            if v[key]:
                w = v[key] * scale
                f.rect(x, y + 3, w - 1.5, 22, fill=color, rx=3)
                if w > 26:
                    f.text(x + w / 2, y + 19, str(v[key]), size=11.5, fill='white', anchor='middle', bold=True)
                x += w
        f.text(x + 8, y + 19, str(sum(v.values())), size=13, fill='ink', bold=True)
    return f


def three_fidelities():
    f = Figure('three-fidelities', 1000, 262, 'Three separate comparisons validate the chain',
               'Capture fidelity compares the object with its reconstruction, CAD fidelity compares the CAD with the observations, and manufacturing fidelity compares the print with the approved CAD. Held-back measurements give an independent check across the chain.')
    nodes = ['Original object', 'Reconstruction', 'Rebuilt CAD', 'Printed part']
    xs = [20, 270, 520, 770]
    for i, (x, label) in enumerate(zip(xs, nodes)):
        f.rect(x, 26, 210, 64, fill='blue' if i in (0, 3) else 'soft', stroke=None if i in (0, 3) else 'line', rx=10)
        f.text(x + 105, 64, label, size=16, fill='white' if i in (0, 3) else 'ink', anchor='middle', bold=True)
        if i < 3:
            f.arrow(x + 214, 58, x + 246, 58, stroke='sky', width=2, head=8)
    labels = [('1 · capture fidelity', 'object vs. reconstruction'), ('2 · CAD fidelity', 'CAD vs. observations & intent'),
              ('3 · manufacturing fidelity', 'print vs. approved CAD')]
    for i, (a, b) in enumerate(labels):
        x1, x2 = xs[i] + 105, xs[i + 1] + 105
        f.polyline([(x1 + 4, 104), (x1 + 4, 116), (x2 - 4, 116), (x2 - 4, 104)], stroke='teal', width=1.8)
        f.text((x1 + x2) / 2, 140, a, size=14, fill='teal', anchor='middle', bold=True)
        f.text((x1 + x2) / 2, 160, b, size=12.5, fill='muted', anchor='middle')
    f.polyline([(129, 184), (129, 198), (871, 198), (871, 184)], stroke='accent', width=1.8, dash=(6, 4))
    f.text(500, 222, 'held-back measurements: an independent check across the whole chain', size=14, fill='accent', anchor='middle', bold=True)
    f.text(500, 244, 'Comparing CAD to a scan only checks agreement with that scan.', size=12.5, fill='muted', anchor='middle')
    return f


def check_tiers():
    f = Figure('check-tiers', 1000, 228, 'Three tiers of checks',
               'Consistency checks show the package agrees with itself, design-rule checks show the design can work, and physical acceptance shows the part works. Report each tier separately.')
    tiers = [('1', 'Consistency', 'files reopen, counts and hashes match, units declared', 'grey', 560),
             ('2', 'Design rules', 'one connected volume, walls, build fit, clearances kept', 'teal', 740),
             ('3', 'Physical acceptance', 'coupons and prints measured against stated criteria', 'blue', 920)]
    for i, (n, name, sub, color, w) in enumerate(tiers):
        x, y = (1000 - w) / 2, 18 + i * 64
        f.rect(x, y, w, 54, fill=color, rx=10)
        f.text(x + 22, y + 34, n, size=22, fill='white', bold=True, family='mono')
        f.text(x + 52, y + 26, name, size=17, fill='white', bold=True)
        f.text(x + 52, y + 44, sub, size=12.5, fill='white')
    f.text(500, 218, 'A passing consistency tier is not validation. Make design-rule failures fail the build.', size=12.5,
           fill='muted', anchor='middle')
    return f


def banner(stats=None):
    sources = load_sources()
    stats = stats or {}
    n_src = len(sources)
    n_repo = sum(1 for s in sources if s['type'] == 'GitHub repository')
    f = Figure('banner', 1200, 340, 'From pictures to printable CAD',
               'Banner: a photograph becomes a dimensioned CAD drawing and then a layered print.', background='deep', border=False)
    for x in range(24, 1200, 24):
        f.line(x, 0, x, 340, stroke='white', width=0.6, alpha=0.06)
    for y in range(24, 340, 24):
        f.line(0, y, 1200, y, stroke='white', width=0.6, alpha=0.06)
    f.text(56, 64, 'FIELD REFERENCE  /  3D & CAD', size=13, fill='accent', bold=True)
    f.text(56, 128, 'From pictures', size=54, fill='white', family='serif')
    f.text(56, 190, 'to printable CAD.', size=54, fill='white', family='serif')
    f.text(56, 228, 'Recover shape · set dimensions · rebuild geometry · check the print', size=16, fill='pale')
    chips = [f'{n_src} sources', f'{n_repo} repositories', f"{stats.get('sections', 22)} chapters",
             f"{stats.get('calculators', 'live')} calculators", 'works offline']
    x = 56
    for c in chips:
        w = 18 + len(c) * 7.6
        f.rect(x, 252, w, 30, fill='white', alpha=0.12, rx=15)
        f.text(x + w / 2, 272, c, size=13, fill='white', anchor='middle', bold=True)
        x += w + 8
    # Stage 1: a photograph of a part.
    f.rect(716, 92, 124, 178, fill='white', rx=6)
    f.rect(725, 101, 106, 112, fill='steel')
    f.polygon([(736, 188), (808, 179), (824, 146), (756, 151)], fill='pale')
    f.ellipse(759, 169, 6.5, 4, fill='steel')
    f.ellipse(798, 163, 6.5, 4, fill='steel')
    f.text(778, 252, 'photo', size=13, fill='muted', anchor='middle', family='mono')
    f.arrow(848, 170, 874, 170, stroke='accent', width=2.5, head=9)
    # Stage 2: a dimensioned plate (60 x 30 mm, 2 x Ø5 at 40 mm), 2 px per mm.
    s, px, py = 2.0, 884, 140
    f.rect(px, py, 60 * s, 30 * s, stroke='white', width=2)
    for dx in (10, 50):
        f.circle(px + dx * s, py + 15 * s, 2.5 * s, stroke='white', width=1.6)
    f.line(px - 8, py + 15 * s, px + 60 * s + 8, py + 15 * s, stroke='pale', width=1, dash=(5, 3))
    f.arrow(px, py - 16, px + 60 * s, py - 16, stroke='pale', width=1.2, head=6, both=True)
    f.text(px + 30 * s, py - 23, '60', size=13, fill='white', anchor='middle', family='mono')
    f.arrow(px + 10 * s, py + 30 * s + 14, px + 50 * s, py + 30 * s + 14, stroke='pale', width=1.2, head=6, both=True)
    f.text(px + 30 * s, py + 30 * s + 32, '40', size=13, fill='white', anchor='middle', family='mono')
    f.text(px + 30 * s, 252, 'CAD', size=13, fill='pale', anchor='middle', family='mono')
    f.arrow(1014, 170, 1040, 170, stroke='accent', width=2.5, head=9)
    # Stage 3: a layered print.
    for i in range(7):
        y = 192 - i * 8
        f.rect(1048 + i * 1.5, y, 112 - i * 3, 9, fill='accent' if i % 2 else 'sand', rx=3)
    f.ellipse(1074, 146, 7, 3.2, fill='deep')
    f.ellipse(1131, 146, 7, 3.2, fill='deep')
    f.text(1102, 252, 'print', size=13, fill='pale', anchor='middle', family='mono')
    f.line(56, 312, 1144, 312, stroke='white', width=1, alpha=0.18)
    return f


FIGURES = {
    'process-flow': process_flow, 'evidence-ladder': evidence_ladder, 'chord-error': chord_error,
    'off-plane-depth': off_plane_depth, 'homography': homography, 'clearance': clearance,
    'route-map': route_map, 'catalog-composition': catalog_composition,
    'three-fidelities': three_fidelities, 'check-tiers': check_tiers, 'banner': banner,
}


def build(name, **kw):
    return FIGURES[name](**kw) if name == 'banner' else FIGURES[name]()
