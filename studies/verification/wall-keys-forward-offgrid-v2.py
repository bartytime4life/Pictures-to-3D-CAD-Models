"""Developer off-grid controls for the sibling Keys-aware forward-model experiment.

Run with --output NEW_JSON; no arguments or --help do not execute the experiment.
The sibling prototype must match its recorded hash and remain unchanged during
execution. Its fixed-local sampling window and supplied-operator assumptions apply;
these controls do not qualify physical geometry, PSF or camera-height inference.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

EXPECTED_PROTOTYPE_SHA256 = 'eb89f4e4a7c4c51b59482e303d848f605c1676518448ab7c0ff21c28b04da2ea'


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='new JSON result; existing files are refused')
    args = parser.parse_args(arguments)
    if args.output.exists():
        parser.error('output already exists; choose a new JSON result path')
    started = time.perf_counter()
    prototype = Path(__file__).with_name('wall-keys-forward-prototype-v1.py')
    prototype_hash = hashlib.sha256(prototype.read_bytes()).hexdigest()
    if prototype_hash != EXPECTED_PROTOTYPE_SHA256:
        raise RuntimeError('sibling prototype hash changed; review it before rerunning these controls')
    spec = importlib.util.spec_from_file_location('wall_keys_local_prototype', prototype)
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)
    sources = {p: hashlib.sha256((model.ROOT / p).read_bytes()).hexdigest() for p in ('backend/edges.py', 'backend/sheet.py')}
    rows = []
    for observation in ('point', 'uniform_pixel_mean'):
        rows.append(model.case('offgrid_single_step_alias', 1.3, 3.25, np.array([60.67, 16.3]), np.array([1., 0.]),
                               .11743, (90., 90., 170.), observation))
        for levels in ((90., 110., 170.), (90., 150., 170.), (90., 165., 170.), (165., 105., 85.)):
            rows.append(model.case('offgrid_bright_wall', 1.3, 3.25, np.array([60.67, 16.3]), np.array([1., 0.]),
                                   2.61371, levels, observation))
    for angle in (37., 143.):
        normal = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
        rows.append(model.case('offgrid_oblique_wall', 1.3, 3.25, np.array([60.67, 16.3]), normal,
                               2.61371, (90., 150., 170.), 'point'))
    assert prototype_hash == hashlib.sha256(prototype.read_bytes()).hexdigest()
    assert sources == {p: hashlib.sha256((model.ROOT / p).read_bytes()).hexdigest() for p in sources}
    summary = []
    for row in rows:
        matched = 'keys_point' if row['observation'] == 'point' else 'keys_uniform_pixel_mean'
        r = row['results'][matched]
        summary.append({'name': row['name'], 'observation': row['observation'], 'levels': row['levels_CBA'],
                        'normal': row['normal'], 'best_edge_error': r['best']['edge_error'],
                        'best_rss': r['best']['rss'], 'ties': r['roundoff_tied_distinct_minima'],
                        'alias': r['single_step_alias_detected']})
    output = args.output
    result = {'format': 'picad-keys-wall-offgrid-prototype', 'version': 2,
              'source_sha256': sources, 'prototype_sha256': prototype_hash,
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=model.ROOT, text=True).strip(),
              'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'seconds': time.perf_counter() - started},
              'sampling_window': 'Current fixed-local _wall_grid_spec verified by the sibling prototype, not its initial expanded-window receipt.',
              'cases': rows, 'summary': summary,
              'limits': 'Same supplied-operator/straight-edge assumptions as prototype v1; no camera-height or production change.'}
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    controls = [r for r in summary if r['name'] != 'offgrid_single_step_alias']
    aliases = [r for r in summary if r['name'] == 'offgrid_single_step_alias']
    print(json.dumps({'result': str(output), 'cases': len(rows), 'seconds': result['runtime']['seconds'],
                      'maximum_nonambiguous_matched_edge_error': max(abs(r['best_edge_error']) for r in controls),
                      'matched_aliases_detected': sum(r['alias'] for r in aliases),
                      'aliases': aliases}, indent=2))


if __name__ == '__main__':
    main()
