"""Developer experiment for a Keys-aware wall forward model, not a product correction.

Run with --output NEW_JSON; no arguments or --help do not execute the experiment.
The ideal input-array field uses independent stdlib erfc. Operator weights intentionally
reuse sheet._keys; sample_keys itself supplies the observed data. Axis pixel means
render with an analytic Gaussian antiderivative and predict with GL16 quadrature.
The sampling window follows the current fixed-local _wall_grid_spec, rather than
the earlier expanded-window experiment. This does not qualify the earlier image
processing chain, optical PSF, physical geometry or camera-height inference.
"""
import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import edges, sheet

ERFC = np.frompyfunc(math.erfc, 1, 1)
GL_X, GL_W = np.polynomial.legendre.leggauss(16)


def cdf(z):
    return .5 * np.asarray(ERFC(-np.asarray(z) / math.sqrt(2)), dtype=float)


def mean_cdf_render(z, sigma):
    """Exact Gaussian step average over an axis-aligned unit pixel, floating evaluation."""
    def h(x):
        return x * cdf(x / sigma) + sigma / math.sqrt(2 * math.pi) * np.exp(-.5 * (x / sigma)**2)
    return h(z + .5) - h(z - .5)


@dataclass
class Operator:
    distance: np.ndarray
    inverse: np.ndarray
    weights: np.ndarray
    t: np.ndarray
    normal: np.ndarray

    def apply(self, raw):
        return np.sum(self.weights * np.asarray(raw)[self.inverse], axis=1)

    def probability(self, location, sigma, model):
        if model == 'continuous':
            return cdf((self.t - location) / sigma)
        if model == 'keys_point':
            return self.apply(cdf((self.distance - location) / sigma))
        if model == 'keys_uniform_pixel_mean':
            assert abs(self.normal[0]) == 1 or abs(self.normal[1]) == 1
            # An axis edge is constant in the other pixel coordinate.
            axis_sign = self.normal[0] if self.normal[0] else self.normal[1]
            value = cdf((self.distance[:, None] - location + .5 * axis_sign * GL_X) / sigma) @ (GL_W / 2)
            return self.apply(value)
        raise ValueError(model)


def operator(seed, normal, t, image_shape):
    """Fixed signed 16-term stencil, clipping INDICES before projecting centres."""
    height, width = image_shape
    x, y = seed[0] + t * normal[0] - .5, seed[1] + t * normal[1] - .5
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - x0, y - y0
    positions, weights = [], []
    for j in range(-1, 3):
        for i in range(-1, 3):
            positions.append(np.column_stack((np.clip(x0 + i, 0, width - 1), np.clip(y0 + j, 0, height - 1))))
            weights.append(sheet._keys(fx - i) * sheet._keys(fy - j))
    positions = np.stack(positions, axis=1)
    unique, inverse = np.unique(positions.reshape(-1, 2), axis=0, return_inverse=True)
    distance = (unique.astype(float) + .5 - seed) @ normal
    return Operator(distance, inverse.reshape(len(t), 16), np.stack(weights, axis=1), t, normal)


def raw_image(bottom, normal, band, sigma, levels, observation, shape=(32, 128)):
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    distance = (xx + .5 - bottom[0]) * normal[0] + (yy + .5 - bottom[1]) * normal[1]
    response = (lambda z: cdf(z / sigma)) if observation == 'point' else (lambda z: mean_cdf_render(z, sigma))
    p1, p2 = response(distance + band), response(distance)
    top, wall, paper = levels
    return top * (1 - p1) + wall * (p1 - p2) + paper * p2


def fit_at(op, profile, band, rate, sigma, edge, model):
    width = max(band - rate * edge, 0.)
    p1, p2 = op.probability(edge - width, sigma, model), op.probability(edge, sigma, model)
    constant = np.ones(len(op.t)) if model == 'continuous' else op.apply(np.ones(len(op.distance)))
    u, v = constant - p1, p1 - p2
    design = np.column_stack((u, v, p2))
    levels, _, rank, _ = np.linalg.lstsq(design, profile, rcond=None)
    if rank != 3:
        return {'edge': edge, 'levels': None, 'rss': math.inf, 'maximum': math.inf}
    wall = float(np.clip(levels[1], 0, 255))
    ends = np.linalg.lstsq(design[:, (0, 2)], profile - wall * v, rcond=None)[0]
    levels = np.array([ends[0], wall, ends[1]])
    residual = profile - design @ levels
    return {'edge': float(edge), 'levels': levels.tolist(), 'rss': float(residual @ residual),
            'maximum': float(np.max(np.abs(residual)))}


def golden(cost, low, high, sigma):
    phi = (math.sqrt(5) - 1) / 2
    a, b = cost(high - phi * (high - low)), cost(low + phi * (high - low))
    for _ in range(48):
        if high - low <= math.sqrt(np.finfo(float).eps) * sigma:
            break
        if a['rss'] <= b['rss']:
            high, b = b['edge'], a
            a = cost(high - phi * (high - low))
        else:
            low, a = a['edge'], b
            b = cost(low + phi * (high - low))
    return min((a, b, cost(low), cost(high)), key=lambda row: row['rss'])


def sampled_minima(cost, grid, sigma):
    rows = [cost(float(e)) for e in grid]
    indices = [i for i in range(1, len(grid) - 1) if rows[i]['rss'] <= rows[i - 1]['rss'] and rows[i]['rss'] <= rows[i + 1]['rss']]
    minima = [min((rows[i], golden(cost, float(grid[i - 1]), float(grid[i + 1]), sigma)), key=lambda row: row['rss']) for i in indices]
    minima.extend((rows[0], rows[-1]))
    return sorted(minima, key=lambda row: row['rss'])


def search(op, profile, band, rate, sigma, candidates, model):
    cost = lambda e: fit_at(op, profile, band, rate, sigma, e, model)
    minima = sampled_minima(cost, candidates, sigma)
    winner = minima[0]
    guard = 64 * np.finfo(float).eps * max(1., float(profile @ profile))
    position_guard = 8 * math.sqrt(np.finfo(float).eps) * max(sigma, abs(winner['edge']))
    tied = [r for r in minima if r['rss'] <= winner['rss'] + guard and abs(r['edge'] - winner['edge']) > position_guard]
    # Global finite-grid one-step witness search; still not a continuous certificate.
    low = max(candidates[0], (1 + rate) * candidates[0] - band)
    high = min(candidates[-1], (1 + rate) * candidates[-1] - band)
    constant = np.ones(len(op.t)) if model == 'continuous' else op.apply(np.ones(len(op.distance)))
    def single(e):
        p = op.probability(e, sigma, model)
        design = np.column_stack((constant - p, p))
        levels, _, rank, _ = np.linalg.lstsq(design, profile, rcond=None)
        levels = np.clip(levels, 0, 255)
        residual = profile - design @ levels
        return {'edge': float(e), 'levels': levels.tolist(), 'rss': float(residual @ residual) if rank == 2 else math.inf}
    single_grid = np.linspace(low, high, max(3, math.ceil((high - low) / (.02 * sigma)) + 1))
    witness = sampled_minima(single, single_grid, sigma)[0]
    partner = (witness['edge'] + band) / (1 + rate)
    alias = partner - witness['edge'] > position_guard and witness['rss'] <= winner['rss'] + guard
    return {'best': winner, 'basins': minima, 'roundoff_tied_distinct_minima': len(tied),
            'single_step_witness': witness, 'single_step_partner': partner,
            'single_step_alias_detected': bool(alias), 'arithmetic_guard': guard}


def case(name, sigma, band_true, true_bottom, normal, seed_error, levels, observation):
    seed = true_bottom - seed_error * normal
    rate = .05
    band_seed = band_true + rate * seed_error
    last, low, high = edges._wall_grid_spec(band_seed, sigma, .125, rate)
    expected_window = math.floor((-band_seed - 4 * sigma) / .125), math.ceil(4 * sigma / .125)
    if (low, high) != expected_window:
        raise RuntimeError('prototype requires the documented fixed-local sampling window')
    candidates, t = np.arange(-30, last + 1) * (.02 * sigma), np.arange(low, high + 1) * .125
    image = raw_image(true_bottom, normal, band_true, sigma, levels, observation)
    profile = sheet.sample_keys(image, seed[0] + t * normal[0] - .5, seed[1] + t * normal[1] - .5)
    op = operator(seed, normal, t, image.shape)
    models = ['continuous', 'keys_point']
    if observation == 'uniform_pixel_mean':
        models.append('keys_uniform_pixel_mean')
    results = {model: search(op, profile, band_seed, rate, sigma, candidates, model) for model in models}
    for result in results.values():
        result['best']['edge_error'] = result['best']['edge'] - seed_error
    matched = 'keys_point' if observation == 'point' else 'keys_uniform_pixel_mean'
    true_fit = fit_at(op, profile, band_seed, rate, sigma, seed_error, matched)
    # Directly compare full true source prediction, without refitting levels.
    width = band_seed - rate * seed_error
    p1, p2 = op.probability(seed_error - width, sigma, matched), op.probability(seed_error, sigma, matched)
    constant = op.apply(np.ones(len(op.distance)))
    prediction = levels[0] * (constant - p1) + levels[1] * (p1 - p2) + levels[2] * p2
    return {'name': name, 'sigma': sigma, 'band_true': band_true, 'band_seed': band_seed,
            'band_rate': rate, 'true_bottom': true_bottom.tolist(), 'normal': normal.tolist(),
            'seed_error': seed_error, 'levels_CBA': list(levels), 'observation': observation,
            'candidate_bounds': [float(candidates[0]), float(candidates[-1])],
            'sampling_bounds': [float(t[0]), float(t[-1])],
            'samples': len(t), 'unique_raw_pixels': len(op.distance),
            'stencil_partition_max_error': float(np.max(np.abs(op.weights.sum(1) - 1))),
            'stencil_max_l1': float(np.max(np.abs(op.weights).sum(1))),
            'matched_operator_true_prediction_max_error': float(np.max(np.abs(prediction - profile))),
            'matched_operator_fit_at_truth': true_fit, 'results': results}


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='new JSON result; existing files are refused')
    args = parser.parse_args(arguments)
    if args.output.exists():
        parser.error('output already exists; choose a new JSON result path')
    started = time.perf_counter()
    sources = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ('backend/edges.py', 'backend/sheet.py')}
    rows = []
    sigma, width = 1.3, 3.25
    for observation in ('point', 'uniform_pixel_mean'):
        rows.append(case('single_step_reported_alias', sigma, width, np.array([60.3, 16.3]), np.array([1., 0.]),
                         0., (90., 90., 170.), observation))
        for wall in (110., 130., 150., 165.):
            rows.append(case('bright_wall_shifted_seed', sigma, width, np.array([60.3, 16.3]), np.array([1., 0.]),
                             2.6, (90., wall, 170.), observation))
    for angle in (37., 143.):
        normal = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
        rows.append(case('oblique_bright_wall', sigma, width, np.array([60.3, 16.3]), normal,
                         2.6, (90., 150., 170.), 'point'))
    # Operator-only edge-replication check; no localization interpretation here.
    seed = np.array([.3, 1.1]); normal = np.array([1., 0.]); t = np.arange(-40, 41) * .125
    image = raw_image(seed, normal, width, sigma, (90., 90., 170.), 'point')
    op = operator(seed, normal, t, image.shape)
    actual = sheet.sample_keys(image, seed[0] + t - .5, np.full_like(t, seed[1] - .5))
    predicted = 90 * op.apply(np.ones(len(op.distance))) + 80 * op.probability(0., sigma, 'keys_point')
    edge_replication = float(np.max(np.abs(predicted - actual)))
    assert sources == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
    result = {'format': 'picad-keys-wall-forward-prototype', 'version': 1,
              'source_sha256': sources, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'seconds': time.perf_counter() - started},
              'sampling_window': 'Fixed local [-band_seed-4*sigma,4*sigma], rounded outward to step0.125 by current _wall_grid_spec; not the initial expanded-window run.',
              'assumptions': ['Known raw sampling coordinates, Keys a=-0.5 weights, exact edge replication and pixel-centre convention.',
                              'Locally infinite straight edge, fixed unit normal and exact constant source tones.',
                              'Known isotropic Gaussian optical spread; axis mean additionally assumes known uniform unit detector aperture.',
                              'The observed input array is ideal point or uniform-mean data, with no prior warp/smoothing/nonlinear response.',
                              'Weights intentionally reuse production sheet._keys; independent erfc fields and actual sample_keys check composition.',
                              'Finite offset grid and bounded local searches supply numerical witnesses, not exhaustive parameter enclosures.'],
              'limits': ['Curvature, nearby boundaries, nonuniform tones, uncertain/correlated PSF and raw-to-rectified composition are absent.',
                         'No production code change, camera-height repair, segmentation/whole-ring benchmark, physical qualification or uncertainty claim.'],
              'edge_replication_prediction_max_error': edge_replication, 'cases': rows}
    output = args.output
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'result': str(output), 'cases': len(rows), 'seconds': result['runtime']['seconds'],
                      'matched_true_prediction_max': max(r['matched_operator_true_prediction_max_error'] for r in rows),
                      'edge_replication_max': edge_replication,
                      'summary': [{'name': r['name'], 'observation': r['observation'], 'wall': r['levels_CBA'][1],
                                   'normal': r['normal'], 'fits': {k: {'e': v['best']['edge'], 'error': v['best']['edge_error'],
                                                                   'rss': v['best']['rss'], 'ties': v['roundoff_tied_distinct_minima'],
                                                                   'alias': v['single_step_alias_detected']}
                                                               for k, v in r['results'].items()}} for r in rows]}, indent=2))


if __name__ == '__main__':
    main()
