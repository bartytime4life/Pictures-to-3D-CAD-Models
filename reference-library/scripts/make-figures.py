"""Write every shared figure to assets/figures/<name>.svg (standard library only).

    python3 scripts/make-figures.py

The HTML builder, the PDF builder, and the README all use these figures. Counts
shown in the banner and the catalog chart are read from the library's own files,
so rerun this script whenever sources.json, HANDBOOK.md, or the calculators change.
A theme-aware copy of the process diagram (CSS variables) goes to tmp/figures-inline/
for the HTML masthead.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figures  # noqa: E402

ROOT = figures.ROOT
out = ROOT / 'assets' / 'figures'
inline = ROOT / 'tmp' / 'figures-inline'
out.mkdir(parents=True, exist_ok=True)
inline.mkdir(parents=True, exist_ok=True)

stats = {
    'sections': len(re.findall(r'^## ', (ROOT / 'HANDBOOK.md').read_text(encoding='utf-8'), flags=re.M)),
    'calculators': len(json.loads((ROOT / 'assets/data/calculators.json').read_text(encoding='utf-8'))),
}
written = []
for name in figures.FIGURES:
    fig = figures.build(name, stats=stats) if name == 'banner' else figures.build(name)
    (out / f'{name}.svg').write_text(fig.to_svg(), encoding='utf-8')
    written.append(name)
(inline / 'process-flow.svg').write_text(figures.process_flow().to_svg(css_vars=True, inline=True), encoding='utf-8')
print(json.dumps({'figures': written, 'stats': stats, 'directory': str(out.relative_to(ROOT))}))
