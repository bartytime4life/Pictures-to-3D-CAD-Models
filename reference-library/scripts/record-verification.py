"""Run the automated checks and write verification.json (standard library only).

    python3 scripts/record-verification.py

Runs the Python and Node test suites and the plate pipeline, then gathers the
browser check (tmp/qa/browser-check.json, from `node scripts/check-library.mjs`),
the optional link check (tmp/qa/link-check.json), the build summary, and the PDF.
Exits non-zero, without writing, if any required check failed or is missing.
VERIFICATION.md explains what these checks do and do not establish.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = json.loads((ROOT / 'library.json').read_text(encoding='utf-8'))
QA = ROOT / 'tmp/qa'
problems: list[str] = []


def run(cmd: list[str], **env) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env={**os.environ, **env} if env else None)


def load(path: Path, required=True):
    if not path.exists():
        if required:
            problems.append(f'missing {path.relative_to(ROOT)}')
        return None
    return json.loads(path.read_text(encoding='utf-8'))


py = run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/python'], CAD_RECORDING_VERIFICATION='1')
py_tail = py.stderr.strip().splitlines()
ran = int(re.search(r'Ran (\d+) tests', py.stderr).group(1)) if 'Ran ' in py.stderr else 0
skipped = int(re.search(r'skipped=(\d+)', py_tail[-1]).group(1)) if py_tail and 'skipped=' in py_tail[-1] else 0
if py.returncode:
    problems.append('python tests failed')

node = shutil.which('node')
node_pass = node_fail = None
if node:
    tests = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'tests/node').glob('*.test.mjs'))
    nd = run([node, '--test', *tests])
    node_pass = int(re.search(r'^# pass (\d+)', nd.stdout, re.M).group(1))
    node_fail = int(re.search(r'^# fail (\d+)', nd.stdout, re.M).group(1))
    if nd.returncode or node_fail:
        problems.append('node tests failed')
else:
    problems.append('node not found')

plate = run([sys.executable, 'examples/build_plate.py'])
plate_rows = []
validation = ROOT / 'examples/output/validation-results.csv'
if plate.returncode:
    problems.append('plate pipeline failed')
elif validation.exists():
    with validation.open(encoding='utf-8', newline='') as fh:
        plate_rows = list(csv.DictReader(fh))
calc = run([sys.executable, 'examples/calculate.py', '--check'])
if calc.returncode:
    problems.append('calculation-results.json is stale')

browser = load(QA / 'browser-check.json') or {}
if browser and browser.get('status') != 'passed':
    problems.append('browser check did not pass')
elif browser:
    if browser.get('revision') != LIB['revision']:
        problems.append('browser check is from another revision; run `make check`')
    if (QA / 'browser-check.json').stat().st_mtime < (ROOT / 'index.html').stat().st_mtime:
        problems.append('index.html changed after the last browser check; run `make check`')
links = load(QA / 'link-check.json', required=False)
build = load(ROOT / 'tmp/build-info.json') or {}
pdf = ROOT / 'output/pdf/pictures-to-printable-cad.pdf'
pdf_bytes = pdf.read_bytes() if pdf.exists() else b''
if not pdf_bytes:
    problems.append('PDF missing')
sources = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
uris = set(re.findall(rb'/URI \((https://[^)]+)\)', pdf_bytes))
pdf_text_urls = sum(1 for s in sources if s['url'].encode() in uris)
if pdf_bytes and pdf_text_urls != len(sources):
    problems.append(f'PDF links {pdf_text_urls} of {len(sources)} catalog URLs')

if problems:
    print(json.dumps({'status': 'failed', 'problems': problems}, indent=2))
    sys.exit(1)

record = {
    'checked_date': LIB['date'],
    'revision': LIB['revision'],
    'status': 'passed',
    'source_records': len(sources),
    'unique_urls': len({s['url'] for s in sources}),
    'github_repositories': sum(1 for s in sources if s['type'] == 'GitHub repository'),
    'handbook_chapters': build.get('handbook_sections'),
    'calculators': build.get('calculators'),
    'figures': build.get('figures'),
    'route_combinations': (build.get('route_inputs') or 0) * (build.get('route_goals') or 0),
    'python_tests': {'ran': ran, 'skipped': skipped, 'status': 'passed'},
    'node_tests': {'passed': node_pass, 'failed': node_fail},
    'browser_checks': {'assertions': browser.get('check_count'), 'local_files_checked': browser.get('local_files_checked'),
                       'in_page_anchors_checked': browser.get('in_page_anchors_checked'),
                       'desktop_viewport': browser.get('desktop_viewport'), 'mobile_viewport': browser.get('mobile_viewport'),
                       'errors': browser.get('browser_errors')},
    'external_links': None if not links else {'checked_at': links['summary']['checked_at'], 'total': links['summary']['total'],
                                               'ok': links['summary']['ok'], 'blocked': links['summary']['blocked'],
                                               'timeout': links['summary']['timeout'], 'broken': links['summary']['broken'],
                                               'not_ok': [x['url'] for x in links['summary']['not_ok']]},
    'pdf_pages': len(re.findall(rb'/Type /Page\b(?!s)', pdf_bytes)),
    'pdf_sha256': hashlib.sha256(pdf_bytes).hexdigest(),
    'pdf_catalog_urls_linked': pdf_text_urls,
    'synthetic_calculations': 'passed',
    'openscad_plate_checks': {'rows': len(plate_rows), 'passed': sum(1 for r in plate_rows if r.get('status') == 'pass')} if plate_rows else 'skipped (OpenSCAD not found)',
    'physical_printing': 'not performed',
    'slicing': 'not performed',
    'reconstruction_benchmarks': 'not performed',
    'scope': 'Automated consistency and design-rule checks of the library, its calculators, and its synthetic CAD examples. No physical part, photograph set, printer, or reconstruction package was qualified.',
}
(ROOT / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps(record, indent=2))
again = run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/python', '-p', 'test_docs.py'])
if again.returncode:
    print(again.stderr, file=sys.stderr)
    sys.exit('verification.json was written but disagrees with VERIFICATION.md or the PDF; update VERIFICATION.md.')
