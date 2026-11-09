"""Build the portable reference book (output/pdf/pictures-to-printable-cad.pdf).

    python3 scripts/make-pdf.py            # needs reportlab and lxml (requirements.txt)

Run scripts/make-figures.py and scripts/build-library.mjs first: this script reads
the HTML fragments they leave in tmp/ and draws the shared figures from
scripts/figures.py natively, so the PDF and the HTML show the same diagrams.

The output is reproducible: ReportLab's invariant mode fixes the creation date
and document ID, so rebuilding unchanged sources gives a byte-identical PDF.
Fonts: DejaVu Sans/Serif/Mono. Set CAD_REFERENCE_FONT_DIR if they are elsewhere.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

from lxml import html
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figures  # noqa: E402

OUT = ROOT / 'output/pdf/pictures-to-printable-cad.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
LIB = json.loads((ROOT / 'library.json').read_text(encoding='utf-8'))
SOURCES = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
REPOS = [s for s in SOURCES if s['type'] == 'GitHub repository']
CALCULATORS = json.loads((ROOT / 'assets/data/calculators.json').read_text(encoding='utf-8'))
FONT_FILES = {'Body': 'DejaVuSans.ttf', 'BodyBold': 'DejaVuSans-Bold.ttf', 'BodyItalic': 'DejaVuSans-Oblique.ttf',
              'Mono': 'DejaVuSansMono.ttf', 'Title': 'DejaVuSerif.ttf', 'TitleBold': 'DejaVuSerif-Bold.ttf'}


def find_font_dir() -> Path:
    candidates = [os.environ.get('CAD_REFERENCE_FONT_DIR'), '/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/dejavu',
                  '/usr/share/fonts/TTF', '/usr/local/share/fonts', str(Path.home() / '.fonts'),
                  str(Path.home() / 'Library/Fonts'), '/Library/Fonts', 'C:/Windows/Fonts']
    for c in filter(None, candidates):
        if (Path(c) / 'DejaVuSans.ttf').exists():
            return Path(c)
    if shutil.which('fc-match'):
        found = subprocess.run(['fc-match', '-f', '%{file}', 'DejaVu Sans'], capture_output=True, text=True).stdout
        if found.endswith('DejaVuSans.ttf'):
            return Path(found).parent
    sys.exit('DejaVu fonts not found. Install fonts-dejavu or set CAD_REFERENCE_FONT_DIR to the folder holding DejaVuSans.ttf.')


FONT = find_font_dir()
for name, file in FONT_FILES.items():
    pdfmetrics.registerFont(TTFont(name, str(FONT / file)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='BodyItalic', boldItalic='BodyBold')

INK = colors.HexColor('#172b37')
BLUE = colors.HexColor('#174d68')
MUTED = colors.HexColor('#566975')
LINE = colors.HexColor('#d4dddf')
WIDTH, HEIGHT = 612, 792
LEFT, RIGHT, TOP, BOTTOM = 51, 51, 60, 52
AVAILABLE = WIDTH - LEFT - RIGHT
styles = {
    'p': ParagraphStyle('body', fontName='Body', fontSize=9.3, leading=14.1, textColor=INK, spaceAfter=8),
    'h1': ParagraphStyle('h1', fontName='Title', fontSize=25, leading=31, textColor=BLUE, spaceAfter=18, keepWithNext=True),
    'h2': ParagraphStyle('h2', fontName='Title', fontSize=17, leading=22, textColor=BLUE, spaceBefore=18, spaceAfter=10, keepWithNext=True),
    'h3': ParagraphStyle('h3', fontName='BodyBold', fontSize=11, leading=15, textColor=INK, spaceBefore=12, spaceAfter=7, keepWithNext=True),
    'small': ParagraphStyle('small', fontName='Body', fontSize=7.7, leading=11, textColor=INK, spaceAfter=5),
    'caption': ParagraphStyle('caption', fontName='BodyItalic', fontSize=7.8, leading=11, textColor=MUTED, spaceBefore=4, spaceAfter=12),
    'cell': ParagraphStyle('cell', fontName='Body', fontSize=7.5, leading=10.7, textColor=INK),
    'cellhead': ParagraphStyle('cellhead', fontName='BodyBold', fontSize=7.5, leading=10.7, textColor=BLUE),
    'bullet': ParagraphStyle('bullet', fontName='Body', bulletFontName='Body', fontSize=9.3, leading=14.1, textColor=INK, leftIndent=14, firstLineIndent=0, bulletIndent=0, spaceAfter=6),
    'cover': ParagraphStyle('cover', fontName='Title', fontSize=35, leading=43, textColor=BLUE, spaceAfter=24),
}


def normalize(t):
    return (t or '').translate(str.maketrans({'–': '-', '—': '-', '‑': '-', '−': '-', '\u00a0': ' '}))


def inline(el):
    text = escape(normalize(el.text))
    for c in el:
        if c.tag in ('ul', 'ol', 'input'):  # nested lists are rendered separately; checkboxes become the bullet
            text += escape(normalize(c.tail))
            continue
        inner = inline(c)
        if c.tag in ('strong', 'b'):
            text += '<b>' + inner + '</b>'
        elif c.tag in ('em', 'i'):
            text += '<i>' + inner + '</i>'
        elif c.tag == 'code':
            text += '<font name="Mono">' + inner + '</font>'
        elif c.tag == 'a':
            href = c.get('href', '')
            text += f'<link href="{escape(href, quote=True)}" color="#174d68">{inner}</link>' if href.startswith('https://') else inner
        elif c.tag == 'br':
            text += '<br/>'
        else:
            text += inner
        text += escape(normalize(c.tail))
    return text


class FigureFlowable(Flowable):
    """Draw one of the shared vector figures at the frame width."""

    def __init__(self, name, width=AVAILABLE):
        super().__init__()
        self.figure = figures.build(name)
        self.width = width
        self.height = width * self.figure.height / self.figure.width

    def draw(self):
        self.figure.draw(self.canv, 0, 0, self.width)


def figure_block(name, caption=None, width=AVAILABLE):
    parts = [FigureFlowable(name, width)]
    if caption:
        parts.append(Paragraph(escape(normalize(caption)), styles['caption']))
    return KeepTogether(parts)


class PlateDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.width = AVAILABLE
        self.height = 285

    def draw(self):
        c = self.canv
        c.setStrokeColor(BLUE)
        c.setFillColor(colors.HexColor('#edf3f6'))
        c.setLineWidth(1)
        x, y, s = 85, 70, 5.5
        c.rect(x, y, 60 * s, 30 * s, fill=1)
        c.setFillColor(colors.white)
        for dx in (10, 50):
            c.circle(x + dx * s, y + 15 * s, 2.5 * s, fill=1)
        c.setStrokeColor(MUTED)
        c.setDash(4, 3)
        c.line(x - 15, y + 15 * s, x + 60 * s + 15, y + 15 * s)
        c.setDash()
        c.setFont('Body', 10)
        c.setFillColor(BLUE)
        c.line(x, y + 30 * s + 15, x + 60 * s, y + 30 * s + 15)
        c.drawCentredString(x + 30 * s, y + 30 * s + 21, '60 mm')
        c.line(x + 10 * s, y - 18, x + 50 * s, y - 18)
        c.drawCentredString(x + 30 * s, y - 33, '40 mm center spacing')
        c.drawString(12, y + 15 * s, '30 mm')
        c.drawString(x, 12, '2 holes: 5 mm diameter   |   Thickness: 4 mm')


class Book(BaseDocTemplate):
    def __init__(self):
        super().__init__(str(OUT), pagesize=(WIDTH, HEIGHT), leftMargin=LEFT, rightMargin=RIGHT,
                         topMargin=TOP, bottomMargin=BOTTOM, invariant=1,
                         title='From pictures to printable CAD - reference handbook',
                         author='Pictures to printable CAD reference library',
                         subject='Photographs, reverse engineering, geometry, CAD and 3D printing',
                         creator=f'scripts/make-pdf.py, revision {LIB["revision"]}')
        frame = Frame(LEFT, BOTTOM, AVAILABLE, HEIGHT - TOP - BOTTOM, id='normal',
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='body', frames=[frame], onPage=self.decorate))

    def decorate(self, c, doc):
        if doc.page == 1:
            return
        c.saveState()
        c.setStrokeColor(LINE)
        c.line(LEFT, HEIGHT - 39, WIDTH - RIGHT, HEIGHT - 39)
        c.setFillColor(MUTED)
        c.setFont('Body', 7.4)
        c.drawString(LEFT, HEIGHT - 30, 'PICTURES TO PRINTABLE CAD  /  REFERENCE LIBRARY')
        c.drawString(LEFT, 28, f'Revision {LIB["revision"]}, {LIB["date_label"]}  |  Links open the cited sources')
        c.drawRightString(WIDTH - RIGHT, 28, str(doc.page))
        c.restoreState()

    def afterFlowable(self, f):
        if hasattr(f, 'toc_key'):
            self.canv.bookmarkPage(f.toc_key)
            self.canv.addOutlineEntry(f.toc_text, f.toc_key, level=0, closed=False)
            self.notify('TOCEntry', (0, f.toc_text, self.page, f.toc_key))


story = []
serial = 0


def heading(text, style='h1', toc=False):
    global serial
    p = Paragraph(escape(normalize(text)), styles[style])
    if toc:
        serial += 1
        p.toc_key = 'section-' + str(serial)
        p.toc_text = normalize(text)
    return p


FIGURE_SRC = re.compile(r'assets/figures/([a-z0-9-]+)\.svg$')


def append_list(el, depth=0):
    """Ordered, bulleted, task (checkbox) and nested lists."""
    style = styles['bullet'] if depth == 0 else ParagraphStyle(f'bullet{depth}', parent=styles['bullet'],
                                                                 leftIndent=14 + 16 * depth, bulletIndent=16 * depth)
    for i, li in enumerate(el.findall('li'), 1):
        box = li.find('input')
        if box is not None and box.get('type') == 'checkbox':
            bullet = '\u2611' if box.get('checked') is not None else '\u2610'
        else:
            bullet = f'{i}.' if el.tag == 'ol' else ('•' if depth == 0 else '–')
        story.append(Paragraph(inline(li).strip(), style, bulletText=bullet))
        for sub in li:
            if sub.tag in ('ul', 'ol'):
                append_list(sub, depth + 1)


def append_html(content, include_h1=True, chapter_toc=False, keep_source_entries=False):
    global serial
    start = len(story)
    doc = html.fragment_fromstring(content, create_parent='div')
    for el in doc:
        tag = el.tag
        if tag in ('h1', 'h2', 'h3', 'h4'):
            if tag == 'h1' and not include_h1:
                continue
            p = Paragraph(inline(el), styles[tag if tag in styles else 'h3'])
            if tag == 'h2' and chapter_toc:
                serial += 1
                p.toc_key = 'section-' + str(serial)
                p.toc_text = normalize(el.text_content())
            story.append(p)
        elif tag == 'p':
            imgs = el.findall('img')
            match = FIGURE_SRC.search(imgs[0].get('src', '')) if len(imgs) == 1 and not (el.text or '').strip() else None
            if match:
                story.append(figure_block(match.group(1), imgs[0].get('title') or imgs[0].get('alt')))
            else:
                story.append(Paragraph(inline(el), styles['p']))
        elif tag in ('ul', 'ol'):
            append_list(el)
            story.append(Spacer(1, 4))
        elif tag == 'table':
            trs = el.findall('.//tr')
            rows = [[Paragraph(inline(td), styles['cellhead' if i == 0 else 'cell']) for td in tr] for i, tr in enumerate(trs)]
            n = len(rows[0])
            table = Table(rows, colWidths=[AVAILABLE / n] * n, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6eef1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7f7')]),
                ('GRID', (0, 0), (-1, -1), .4, LINE), ('LEFTPADDING', (0, 0), (-1, -1), 7),
                ('RIGHTPADDING', (0, 0), (-1, -1), 7), ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
            story.extend([Spacer(1, 8), table, Spacer(1, 12)])
        elif tag == 'hr':
            story.append(Spacer(1, 12))
    if keep_source_entries:
        grouped, group = [], []
        for item in story[start:]:
            is_heading = isinstance(item, Paragraph) and item.style.name in ('h1', 'h2', 'h3')
            if is_heading and group:
                grouped.append(KeepTogether(group))
                group = []
            if isinstance(item, Paragraph) and item.style.name == 'h3':
                group = [item]
            elif group:
                group.append(item)
            else:
                grouped.append(item)
        if group:
            grouped.append(KeepTogether(group))
        story[start:] = grouped


# ---- cover ---------------------------------------------------------------------
story.extend([
    Spacer(1, 10), FigureFlowable('banner'), Spacer(1, 26),
    Paragraph('Recover shape. Establish dimensions. Build editable geometry. Check the part you print.', styles['h2']),
    Spacer(1, 10), FigureFlowable('process-flow'), Spacer(1, 22),
    Paragraph(f'{len(SOURCES)} annotated resources · {len(REPOS)} GitHub projects · Practical workflows · '
              f'Advanced geometry · {len(CALCULATORS)} calculators · Reusable worksheets', styles['p']),
    Paragraph(f'Prepared {LIB["date_label"]} · Revision {LIB["revision"]}', styles['p']), Spacer(1, 14),
    Paragraph('A source-backed learning and reference package. Synthetic examples are labeled. No real reconstruction, '
              'software benchmark, or physical print qualification is implied.', styles['small']),
    PageBreak()])
story.append(heading('Contents'))
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle('toc', fontName='Body', fontSize=8.7, leading=12.5, textColor=BLUE, spaceBefore=0,
                                  leftIndent=0, firstLineIndent=0, rightIndent=15)]
story.extend([toc, PageBreak()])
append_html((ROOT / 'tmp/HANDBOOK.html').read_text(encoding='utf-8'), include_h1=False, chapter_toc=True)
story.extend([PageBreak(), heading('Research map and evidence notes', toc=True)])
append_html((ROOT / 'tmp/RESEARCH-NOTES.html').read_text(encoding='utf-8'), include_h1=False)
story.extend([PageBreak(), heading('Annotated source directory', toc=True),
              figure_block('catalog-composition', 'Catalog composition by topic and review depth, drawn from sources.json.')])
append_html((ROOT / 'tmp/REFERENCES.html').read_text(encoding='utf-8'), include_h1=False, keep_source_entries=True)
story.extend([PageBreak(), heading('Synthetic two-hole plate', toc=True),
              Paragraph('This diagram accompanies the editable OpenSCAD source and its parameter register '
                        '(examples/plate-parameters.csv). All values are illustrative, with no real photograph, dimensional '
                        'inspection, fit test, or physical printing result.', styles['p']),
              PlateDiagram(),
              Paragraph('OpenSCAD 2021.01 rendered the source; examples/build_plate.py checked the STL for its 60 x 30 x 4 mm '
                        'extents, a single closed and consistently oriented component, and minimum walls (examples/README.md). '
                        'No part was sliced or printed. The Python calculation script checks the handbook\u2019s scale, '
                        'uncertainty, tessellation, gear, calibration-proportion, off-plane depth, camera-distance, '
                        'label-rounding, and coating arithmetic.', styles['p'])])
story.extend([PageBreak(), heading('Project worksheets', toc=True)])
for name in ['PROJECT-BRIEF', 'CAPTURE-CHECKLIST', 'PRINT-ACCEPTANCE', 'INDEPENDENT-CHECKS']:
    append_html((ROOT / 'tmp' / f'{name}.html').read_text(encoding='utf-8'))
    if name != 'INDEPENDENT-CHECKS':
        story.append(PageBreak())
Book().multiBuild(story)
print(OUT)
