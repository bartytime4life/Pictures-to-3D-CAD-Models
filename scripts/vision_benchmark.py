"""Score the photo library's vision features on rendered photographs with known truth.

    .venv/bin/python scripts/vision_benchmark.py              score with the shipped thresholds
    .venv/bin/python scripts/vision_benchmark.py --calibrate  show how thresholds were chosen
    .venv/bin/python scripts/vision_benchmark.py --all        all fourteen parts at once (harder)

What it does
    Renders flat parts on varied backgrounds (scripts/vision_scenes.py), adds exact,
    re-saved and half-size copies of some shots, indexes the folder with the real
    library pipeline and the installed vision model, and compares the result with what
    was rendered.

    Thresholds are chosen on seven of the fourteen parts (--calibrate) and scored on the
    other seven, rendered with another seed, so the scored parts were never seen when
    the thresholds were set.

What it does not show
    The pictures are drawings of plates and gaskets under simulated light. The scores
    say how the pipeline behaves on these shapes and variations. They are not accuracy
    figures for photographs of real parts.

Set PICAD_VISION_MODEL to score one model (vits16, vits16plus, vitb16, vitl16).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import vision_scenes

CALIBRATION_SEED, EVALUATION_SEED = 2026, 4051
VIEWS = 8
COPIES_OF = 2  # Shots of each part that also get an exact, a re-saved and a half-size copy.


def split_parts():
    names = sorted(vision_scenes.parts())
    return names[0::2], names[1::2]


def build_folder(folder: Path, names, seed) -> dict:
    """Render the set into ``folder``. Returns file name -> truth (with 'copy_of' for copies)."""
    truth = {}
    per_part: dict[str, int] = {}
    for name, data, facts in vision_scenes.dataset(VIEWS, seed, names):
        (folder / name).write_bytes(data)
        truth[name] = {**facts, "copy_of": None, "copy": None}
        seen = per_part.get(facts["part"], 0)
        per_part[facts["part"]] = seen + 1
        if seen >= COPIES_OF:
            continue
        stem = name[: -len(".jpg")]
        picture = Image.open(io.BytesIO(data)).convert("RGB")
        (folder / f"{stem}-exact.jpg").write_bytes(data)
        buffer = io.BytesIO()
        picture.save(buffer, "JPEG", quality=60)
        (folder / f"{stem}-resaved.jpg").write_bytes(buffer.getvalue())
        buffer = io.BytesIO()
        picture.resize((picture.width // 2, picture.height // 2), Image.Resampling.LANCZOS).save(buffer, "JPEG", quality=88)
        (folder / f"{stem}-half.jpg").write_bytes(buffer.getvalue())
        for kind in ("exact", "resaved", "half"):
            truth[f"{stem}-{kind}.jpg"] = {**facts, "copy_of": name, "copy": kind}
    return truth


def index(folder: Path):
    """Run the real library pipeline on ``folder``. Returns (stage seconds, summary)."""
    from backend import library

    library.add_folder(str(folder))
    seconds = {}
    last = {"stage": None, "at": time.time()}
    library.start_crunch()
    while True:
        state = library.job.state()
        if state.get("stage") != last["stage"]:
            now = time.time()
            if last["stage"]:
                seconds[last["stage"]] = seconds.get(last["stage"], 0) + now - last["at"]
            last = {"stage": state.get("stage"), "at": now}
        if not state["running"]:
            break
        time.sleep(0.02)
    if state["error"]:
        raise SystemExit(f"The crunch failed: {state['error']}")
    return seconds, state["summary"]


def load(truth):
    """Library rows and vectors aligned with the rendered truth."""
    from backend import library

    rows = {}
    offset = 0
    while True:
        page = library.list_photos(sort="name", offset=offset, limit=500)
        for photo in page["photos"]:
            rows[photo["name"]] = photo
        offset += 500
        if offset >= page["total"]:
            break
    loaded = library.vectors.load()
    place = {int(photo_id): i for i, photo_id in enumerate(loaded.ids)}
    names = sorted(truth)
    order = [place[rows[name]["id"]] for name in names]
    return names, rows, loaded.whole[order], loaded.subject[order], loaded.model


def iou_boxes(a, b):
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - width * height
    return width * height / union if union > 0 else 0.0


def subject_scores(names, rows, truth):
    from backend import library

    region_iou, box_iou, found = [], [], 0
    for name in names:
        facts = truth[name]
        if facts["copy_of"]:
            continue
        detail = library.get_photo(rows[name]["id"])
        mask = facts["mask"]
        height, width = mask.shape
        if "subject" not in detail or "box" not in detail:
            region_iou.append(0.0)
            box_iou.append(0.0)
            continue
        found += 1
        grid = detail["subject"]["grid"]
        region = np.array([[cell == "1" for cell in line] for line in detail["subject"]["rows"]])
        ys = np.minimum((np.arange(height) * grid) // height, grid - 1)
        xs = np.minimum((np.arange(width) * grid) // width, grid - 1)
        predicted = region[np.ix_(ys, xs)]
        region_iou.append(float((predicted & mask).sum() / max((predicted | mask).sum(), 1)))
        x0, y0, x1, y1 = facts["box"]
        box_iou.append(iou_boxes(detail["box"], (x0 / width, y0 / height, x1 / width, y1 / height)))
    return {
        "photos": len(region_iou),
        "subject_found": found,
        "region_iou_mean": float(np.mean(region_iou)),
        "region_iou_median": float(np.median(region_iou)),
        "region_iou_min": float(np.min(region_iou)),
        "box_iou_mean": float(np.mean(box_iou)),
        "box_iou_below_half": int((np.array(box_iou) < 0.5).sum()),
    }


def matching_scores(labels, vectors):
    """Precision of the first match and mean average precision, by cosine."""
    scores = vectors @ vectors.T
    np.fill_diagonal(scores, -np.inf)
    order = np.argsort(-scores, axis=1)
    first = float((labels[order[:, 0]] == labels).mean())
    precisions = []
    for i in range(len(labels)):
        relevant = labels[order[i, :-1]] == labels[i]
        hits = np.cumsum(relevant)
        precisions.append(float((hits[relevant] / (np.flatnonzero(relevant) + 1)).mean()))
    return {"first_match": first, "mean_average_precision": float(np.mean(precisions))}


def pair_scores(labels, groups):
    """Of all pairs put in one group, the share truly the same part (precision); of all
    true same-part pairs, the share put in one group (recall)."""
    same_truth = labels[:, None] == labels[None, :]
    same_group = groups[:, None] == groups[None, :]
    upper = np.triu(np.ones_like(same_truth, bool), 1)
    together, true = (same_group & upper).sum(), (same_truth & upper).sum()
    correct = (same_group & same_truth & upper).sum()
    precision = correct / together if together else 1.0
    recall = correct / true if true else 1.0
    return float(precision), float(recall), float(2 * precision * recall / max(precision + recall, 1e-12))


def copy_cosines(names, truth, whole):
    """Whole-picture cosines of true copy pairs, and the largest between two different shots."""
    place = {name: i for i, name in enumerate(names)}
    copies = {"exact": [], "resaved": [], "half": []}
    for name in names:
        if truth[name]["copy_of"]:
            copies[truth[name]["copy"]].append(float(whole[place[name]] @ whole[place[truth[name]["copy_of"]]]))
    originals = [i for i, name in enumerate(names) if not truth[name]["copy_of"]]
    scores = whole[originals] @ whole[originals].T
    np.fill_diagonal(scores, -np.inf)
    return copies, float(scores.max())


def lookalike_scores(names, rows, truth):
    """Copies the library flagged, and different shots it wrongly linked."""
    found = {"exact": 0, "resaved": 0, "half": 0}
    total = {"exact": 0, "resaved": 0, "half": 0}
    for name in names:
        source = truth[name]["copy_of"]
        if source:
            total[truth[name]["copy"]] += 1
            same = rows[name]["dup_set"] is not None and rows[name]["dup_set"] == rows[source]["dup_set"]
            found[truth[name]["copy"]] += int(same)
    sets: dict[int, set] = {}
    for name in names:
        if rows[name]["dup_set"] is not None:
            sets.setdefault(rows[name]["dup_set"], set()).add(truth[name]["copy_of"] or name)
    wrong = sum(1 for originals in sets.values() if len(originals) > 1)
    return {"found": found, "of": total, "sets_mixing_different_shots": wrong}


def best_shot_scores(names, rows, truth):
    """Whether each group's best shot is the truly most detailed one.

    True detail is the part's rendered long side in pixels over the rendered blur. A
    group's shots are ranked by it; rank 1 is the truly most detailed. Copies stand for
    the shot they were made from, and a half-size copy has half the detail.
    """

    def true_detail(name):
        x0, y0, x1, y1 = truth[name]["box"]
        scale = 0.5 if truth[name]["copy"] == "half" else 1.0
        return scale * max(x1 - x0, y1 - y0) / truth[name]["blur_px"]

    ranks = []
    for name in names:
        if not rows[name]["best"]:
            continue
        members = [n for n in names if rows[n]["group_id"] == rows[name]["group_id"]]
        better = sum(true_detail(n) > true_detail(name) + 1e-9 for n in members)
        ranks.append(better + 1)
    return {
        "groups": len(ranks),
        "truly_most_detailed": sum(rank == 1 for rank in ranks),
        "within_top_three": sum(rank <= 3 for rank in ranks),
        "mean_group_size": round(float(np.mean([sum(rows[n]["group_id"] == rows[b]["group_id"] for n in names) for b in names if rows[b]["best"]])), 1) if ranks else 0,
    }


def rank_correlation(a, b):
    ranks = lambda v: np.argsort(np.argsort(v)).astype(float)
    return float(np.corrcoef(ranks(np.asarray(a)), ranks(np.asarray(b)))[0, 1])


def run(names, seed, calibrate):
    from backend import library, vision

    with tempfile.TemporaryDirectory(prefix="picad-vision-") as scratch:
        os.environ["PICAD_LIBRARY_DIR"] = str(Path(scratch) / "library")
        folder = Path(scratch) / "photos"
        folder.mkdir()
        truth = build_folder(folder, names, seed)
        seconds, summary = index(folder)
        if "skipped" in summary.get("features", {}):
            raise SystemExit(f"The vision model is not available: {summary['features']['skipped']}")
        ordered, rows, whole, subject, model = load(truth)
        info = vision.model_info(model)
        labels = np.array([truth[name]["part"] for name in ordered])
        originals = np.array([truth[name]["copy_of"] is None for name in ordered])
        report = {
            "model": info["name"],
            "device": (vision.engine.runtime() or {}).get("device_name"),
            "photos": len(ordered),
            "parts": len(set(labels)),
            "seconds": {stage: round(value, 2) for stage, value in seconds.items()},
            "subject": subject_scores(ordered, rows, truth),
            "matching_subject": matching_scores(labels[originals], subject[originals]),
            "matching_whole": matching_scores(labels[originals], whole[originals]),
        }
        shots = [name for name, original in zip(ordered, originals, strict=True) if original]
        for key, label in (("blur_px", "blur_rank_correlation"), ("subject_blur_px", "subject_blur_rank_correlation")):
            pairs = [(truth[name]["blur_px"], rows[name][key]) for name in shots if rows[name][key]]
            report[label] = round(rank_correlation(*zip(*pairs, strict=True)), 3)
            report[label + "_photos"] = len(pairs)
        copies, largest_other = copy_cosines(ordered, truth, whole)
        report["copy_cosine_min"] = {kind: round(min(values), 4) for kind, values in copies.items()}
        report["different_shot_cosine_max"] = round(largest_other, 4)
        if calibrate:
            # Every link threshold with every split threshold at or below it. Rows: link,
            # split, pair precision, recall, F1. Chosen: of the pairs within 0.02 of the
            # best F1, the strictest (highest split, then highest link), because a group
            # that wrongly merges two parts hides one of them.
            from backend import library, vision_math

            near, cosines = vision_math.neighbours(subject[originals], library.NEIGHBOURS)
            grid = []
            for link in np.arange(0.76, 0.921, 0.02):
                linked = vision_math.linked_groups(near, cosines, float(link))
                for split in np.arange(0.70, float(link) + 0.001, 0.02):
                    groups = vision_math.split_chained(subject[originals], linked, float(split))
                    precision, recall, f1 = pair_scores(labels[originals], groups)
                    grid.append([round(float(link), 2), round(float(split), 2), round(precision, 3), round(recall, 3), round(f1, 3)])
            best = max(row[4] for row in grid)
            chosen = max((row for row in grid if row[4] >= best - 0.02), key=lambda row: (row[1], row[0]))
            report["group_grid_best_f1"] = best
            report["group_thresholds_chosen"] = {"link": chosen[0], "split": chosen[1], "precision": chosen[2], "recall": chosen[3], "f1": chosen[4]}
            report["group_thresholds_shipped"] = {"link": info["group"], "split": info["split"]}
            lowest_copy = min(min(values) for kind, values in copies.items() if kind != "exact")
            report["lookalike_gap"] = [round(largest_other, 4), round(lowest_copy, 4)]
        else:
            group_ids = np.array([rows[n]["group_id"] if rows[n]["group_id"] is not None else -rows[n]["id"] for n in ordered])
            precision, recall, f1 = pair_scores(labels[originals], group_ids[originals])
            report["groups"] = {
                "threshold": info["group"],
                "split": info["split"],
                "pair_precision": round(precision, 3),
                "pair_recall": round(recall, 3),
                "f1": round(f1, 3),
                "groups_found": summary["organize"]["groups"],
            }
            report["copies"] = {"threshold": info["lookalike"], **lookalike_scores(ordered, rows, truth)}
            report["best_shots"] = best_shot_scores(ordered, rows, truth)
        library.clear()
        vision.engine.close()
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--calibrate", action="store_true", help="sweep thresholds on the calibration parts")
    parser.add_argument(
        "--all", action="store_true", help="score all fourteen parts together (includes the calibration parts)"
    )
    parser.add_argument("--json", metavar="FILE", help="also write the report as JSON")
    args = parser.parse_args()
    calibration, evaluation = split_parts()
    if args.all:
        names, seed, label = sorted(calibration + evaluation), EVALUATION_SEED, "all parts (not held out)"
    elif args.calibrate:
        names, seed, label = calibration, CALIBRATION_SEED, "calibration"
    else:
        names, seed, label = evaluation, EVALUATION_SEED, "evaluation"
    report = run(names, seed, args.calibrate and not args.all)
    report["set"] = label
    report["part_names"] = names
    print(json.dumps(report, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
