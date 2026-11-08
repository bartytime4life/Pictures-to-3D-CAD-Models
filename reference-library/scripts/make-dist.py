"""Write the checksum manifest and the portable archive (standard library only).

    python3 scripts/make-dist.py           # write SHA256SUMS and the ZIP in dist/
    python3 scripts/make-dist.py --check   # verify SHA256SUMS against the files; exit 1 on mismatch

Paths in SHA256SUMS are relative to the folder above reference-library/ (the
repository root), so ``sha256sum -c reference-library/SHA256SUMS`` works from
there. The ZIP uses sorted entries, fixed timestamps (library.json date) and
fixed permissions, so unchanged sources give a byte-identical archive. Only
reference-library/ is packaged; generated scratch (tmp/, dist/, examples/output/,
node_modules/, caches) is not. SHA256SUMS and dist/ are build products and are
not committed.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parent.parent
TOP = LIB_DIR.parent
LIB = json.loads((LIB_DIR / 'library.json').read_text(encoding='utf-8'))
MANIFEST = LIB_DIR / 'SHA256SUMS'
ARCHIVE = LIB_DIR / 'dist' / LIB['archive_name']
EXCLUDE_DIRS = {'tmp', 'dist', 'node_modules', '__pycache__', '.pytest_cache', '.git'}
EXCLUDE_PATHS = {'examples/output'}
EXCLUDE_NAMES = {'.DS_Store', 'SHA256SUMS', 'Thumbs.db'}


def library_files() -> list[Path]:
    files = []
    for p in sorted(LIB_DIR.rglob('*')):
        rel = p.relative_to(LIB_DIR)
        if not p.is_file() or p.name in EXCLUDE_NAMES or p.suffix == '.pyc':
            continue
        if set(rel.parts) & EXCLUDE_DIRS or any(rel.as_posix().startswith(x + '/') for x in EXCLUDE_PATHS):
            continue
        files.append(p)
    return sorted(files, key=lambda p: p.relative_to(TOP).as_posix())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def check() -> int:
    bad = []
    for line in MANIFEST.read_text(encoding='utf-8').splitlines():
        digest, name = line.split('  ', 1)
        path = TOP / name
        if not path.exists():
            bad.append(f'missing: {name}')
        elif sha256(path) != digest:
            bad.append(f'changed: {name}')
    listed = {line.split('  ', 1)[1] for line in MANIFEST.read_text(encoding='utf-8').splitlines()}
    bad += [f'not in manifest: {p}' for p in (f.relative_to(TOP).as_posix() for f in library_files()) if p not in listed]
    print(json.dumps({'manifest': str(MANIFEST.relative_to(TOP)), 'entries': len(listed), 'problems': bad}, indent=2))
    return 1 if bad else 0


def main() -> int:
    if '--check' in sys.argv:
        return check()
    files = library_files()
    MANIFEST.write_text(''.join(f'{sha256(p)}  {p.relative_to(TOP).as_posix()}\n' for p in files), encoding='utf-8')
    stamp = tuple(int(x) for x in LIB['date'].split('-')) + (12, 0, 0)
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files + [MANIFEST]:
            info = zipfile.ZipInfo(p.relative_to(TOP).as_posix(), date_time=stamp)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, p.read_bytes(), compresslevel=9)
    print(json.dumps({'files': len(files), 'manifest': str(MANIFEST.relative_to(TOP)),
                      'archive': str(ARCHIVE.relative_to(TOP)), 'archive_bytes': ARCHIVE.stat().st_size,
                      'archive_sha256': sha256(ARCHIVE)}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
