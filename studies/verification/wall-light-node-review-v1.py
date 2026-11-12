"""Read-only independent check of the proposed wall-gradient study primitives."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PARENT = HERE.parents[1] / 'scripts/wall_gradient_study.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new JSON result; existing files refused')
    args = parser.parse_args()
    before = hashlib.sha256(PARENT.read_bytes()).hexdigest()
    oracle = load(HERE / 'wall-light-identifiability-oracle-v1.py', 'wall_light_independent')
    study = load(PARENT, 'wall_light_study_reviewed')
    basis_cases = []
    for sigma in (0.85, 1.65):
        for width in (0, 0.15, 0.4, 1.0, 2.5, 4.0):
            for edge in (-0.5 * sigma, 0.5 * sigma):
                band, tail = width * sigma, 12 * sigma
                t = np.linspace(-15 * sigma, 15 * sigma, 151)
                matrix = study.source_basis(t, edge, band, sigma, tail)
                quadrature = np.column_stack([oracle.source_integral(t, edge, band, sigma, tail, node, 16)
                                               for node in np.eye(5)])
                checked = np.column_stack([oracle.source_integral(t, edge, band, sigma, tail, node, 8)
                                            for node in np.eye(5)])
                basis_cases.append({'sigma': sigma, 'band_sigmas': width, 'edge': edge,
                                    'basis_vs_quadrature_max': float(np.max(np.abs(matrix - quadrature))),
                                    'quadrature_8_vs_16_max': float(np.max(np.abs(checked - quadrature))),
                                    'partition_max': float(np.max(np.abs(matrix.sum(1) - 1))),
                                    'minimum_basis': float(matrix.min())})

    rng = np.random.default_rng(731904)
    fit_cases = []
    for dimension in range(1, 6):
        for sample in range(10):
            matrix = rng.normal(size=(19, dimension))
            if sample == 8 and dimension > 1:
                matrix[:, -1] = matrix[:, 0]
            if sample == 9:
                matrix[:, -1] = 0
            y = matrix @ rng.uniform(-80, 335, dimension) + rng.normal(size=19)
            beta, solves = study.bounded_projection(matrix, y)
            residual = matrix @ beta - y
            gradient = matrix.T @ residual
            lower, upper = beta == 0, beta == 255
            free = ~(lower | upper)
            violation = max(float(np.max(np.maximum(-gradient[lower], 0), initial=0)),
                            float(np.max(np.maximum(gradient[upper], 0), initial=0)),
                            float(np.max(np.abs(gradient[free]), initial=0)))
            fit_cases.append({'dimension': dimension, 'case': sample, 'faces_solved': solves,
                              'feasible': bool(np.all((beta >= 0) & (beta <= 255))),
                              'kkt_max_violation': violation,
                              'gradient_scale': float(np.linalg.norm(matrix) * np.linalg.norm(residual))})

    # Compare the true geometry and bounded shifted witness by independent source integration.
    sigma, band, tail = 2.0, 0.2, 24.0
    t = np.arange(-(band + 4 * sigma), 4 * sigma + 0.125 / 2, 0.125)
    truth = np.array([66, 89.8, 130, 170, 146])
    observed = oracle.source_integral(t, 0, band, sigma, tail, truth, 16)
    design = study.source_basis(t, 0.5, band, sigma, tail)
    beta, solves = study.bounded_projection(design, observed)
    residual = oracle.source_integral(t, 0.5, band, sigma, tail, beta, 16) - observed
    boundary_case = {'sigma': sigma, 'band': band, 'edge': 0.5, 'nodes': beta.tolist(),
                     'faces_solved': solves, 'maximum_difference': float(np.max(np.abs(residual))),
                     'rms': float(np.sqrt(np.mean(residual * residual)))}

    after = hashlib.sha256(PARENT.read_bytes()).hexdigest()
    assert before == after, 'parent study source changed during verification'
    result = {'reviewed_source': str(PARENT), 'reviewed_source_sha256': before,
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'basis_cases': basis_cases, 'box_kkt_cases': fit_cases,
              'boundary_active_case': boundary_case,
              'limits': 'Floating-point quadrature/KKT checks, no interval certification or physical error prior'}
    destination = args.output
    with destination.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'result': str(destination), 'source_sha256': before,
                      'basis_cases': len(basis_cases), 'box_kkt_cases': len(fit_cases),
                      'max_basis_quadrature_delta': max(r['basis_vs_quadrature_max'] for r in basis_cases),
                      'max_quadrature_delta': max(r['quadrature_8_vs_16_max'] for r in basis_cases),
                      'max_box_kkt_violation': max(r['kkt_max_violation'] for r in fit_cases),
                      'all_box_fits_feasible': all(r['feasible'] for r in fit_cases),
                      'active_case': boundary_case}, indent=2))


if __name__ == '__main__':
    main()
