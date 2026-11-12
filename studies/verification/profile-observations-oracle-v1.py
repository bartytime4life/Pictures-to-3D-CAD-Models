"""Read-only independent checks of the conditional fixed linear sampling model."""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.profile_observations import PixelNoise, keys_profile
from backend.sheet import sample_keys


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new JSON result; existing paths are refused")
    args = parser.parse_args(arguments)
    if args.output.exists():
        parser.error("output exists; choose a fresh JSON result path")
    paths = ['backend/profile_observations.py', 'backend/sheet.py', 'scripts/profile_noise_study.py']
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    started = time.perf_counter()
    rng = np.random.default_rng(599131)
    errors = {"covariance": 0., "heterogeneous_identity": 0., "fitted_coefficients": 0.,
              "residual_cost": 0., "duplicate_information": 0., "filter_composition": 0.}
    for k in range(24):
        source_count = 3 + k % 6
        samples = source_count + 2 + k % 3
        matrix = rng.normal(size=(samples, source_count))
        std = np.exp(rng.uniform(-1.2, 1.2, size=source_count))
        noise = PixelNoise.factor(matrix, std)
        white_operator = noise.whiten(matrix * std)
        errors['covariance'] = max(errors['covariance'], float(np.max(np.abs(white_operator @ white_operator.T - np.eye(source_count)))))
        source = rng.normal(size=(source_count, 2))
        errors['heterogeneous_identity'] = max(errors['heterogeneous_identity'], float(np.max(np.abs(noise.whiten(matrix @ source) - noise.whiten_source(source)))))
        design = np.column_stack((np.ones(source_count), np.linspace(-1, 1, source_count)))
        raw = rng.normal(size=source_count)
        expected_coeff = np.linalg.lstsq(design / std[:, None], raw / std, rcond=None)[0]
        fit = noise.fit_source(design, matrix @ raw)
        errors['fitted_coefficients'] = max(errors['fitted_coefficients'], float(np.max(np.abs(expected_coeff-fit['coefficients']))))
        expected_cost = float(np.sum(((raw-design @ expected_coeff)/std)**2))
        errors['residual_cost'] = max(errors['residual_cost'], abs(expected_cost-fit['squared_whitened_residual']))
        repeated = PixelNoise.factor(np.repeat(matrix, 3, axis=0), std)
        direction = rng.normal(size=source_count)
        information = float(noise.whiten_source(direction) @ noise.whiten_source(direction))
        repeated_information = float(repeated.whiten_source(direction) @ repeated.whiten_source(direction))
        errors['duplicate_information'] = max(errors['duplicate_information'], abs(information-repeated_information))

    filter_cases = 0
    for shape in [(1, 1), (1, 13), (11, 1), (11, 13)]:
        image = rng.normal(size=shape)
        x = rng.uniform(-2, shape[1]+2, size=7)
        y = rng.uniform(-2, shape[0]+2, size=7)
        op = keys_profile(shape, x, y)
        for filter_shape in [(1, 1), (3, 5), (15, 1)]:
            kernel = rng.normal(size=filter_shape) / math.prod(filter_shape)
            for border, cvborder in [('replicate', cv2.BORDER_REPLICATE), ('reflect101', cv2.BORDER_REFLECT_101)]:
                composed = op.after_filter(kernel, border=border)
                actual = sample_keys(cv2.filter2D(image, -1, kernel, borderType=cvborder), x, y)
                errors['filter_composition'] = max(errors['filter_composition'], float(np.max(np.abs(composed.sample(image)-actual))))
                filter_cases += 1

    matrix = np.array([[1., -.2, 0.], [0., .5, .5], [.2, .8, 0.], [1., -.2, 0.]])
    std = np.array([.4, 1.7, 2.3])
    noise = PixelNoise.factor(matrix, std)
    direction = np.array([.3, -.7, .2])
    h = noise.whiten_source(direction)
    info = float(h @ h)
    raw_standard_draws = rng.normal(size=(100000, 3))
    # Direct independent derivation from the profile response and covariance pseudoinverse.
    covariance = (matrix * std) @ (matrix * std).T
    sampled_direction = matrix @ direction
    covariance_inverse = np.linalg.pinv(covariance, hermitian=True)
    weights = covariance_inverse @ sampled_direction / float(sampled_direction @ covariance_inverse @ sampled_direction)
    profile_draws = (raw_standard_draws * std) @ matrix.T
    trial = profile_draws @ weights
    stable_trial = (raw_standard_draws @ noise.right.T) @ h / info
    mc = {'draws': len(trial), 'predicted_variance': 1/info, 'empirical_variance_ddof_1': float(np.var(trial, ddof=1)), 'maximum_direct_vs_source_trial_delta': float(np.max(np.abs(trial-stable_trial)))}

    counterexample = PixelNoise.factor([[1.], [1.]], 1.).residual([1., -1.], [0., 0.])
    assert errors['covariance'] < 1e-13
    assert errors['heterogeneous_identity'] < 1e-12
    assert errors['fitted_coefficients'] < 1e-12
    assert errors['residual_cost'] < 1e-11
    assert errors['duplicate_information'] < 1e-11
    assert errors['filter_composition'] < 5e-14
    assert mc['maximum_direct_vs_source_trial_delta'] < 1e-13
    assert abs(mc['empirical_variance_ddof_1']/mc['predicted_variance']-1) < .02
    assert not counterexample['within_retained_support_tolerance']
    assert hashes == {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    result = {'format': 'independent-profile-observations-review', 'version': 1, 'source_sha256': hashes, 'random_seed': 599131, 'heterogeneous_cases': 24, 'filter_composition_cases': filter_cases, 'maximum_absolute_errors': errors, 'heterogeneous_gaussian_linear_estimator': mc, 'outside_support_control': counterexample, 'runtime_seconds': time.perf_counter()-started, 'limits': ['Algebraic and synthetic operator controls only.', 'No physical noise calibration, nonlinear-estimator coverage, production integration or full suite.', 'Gaussian raw pixels are a supplied hypothesis.']}
    result["runner_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    content = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(content)
    print(f"Recorded {result["heterogeneous_cases"]} fit controls, {filter_cases} filter controls and 100000 draws to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
