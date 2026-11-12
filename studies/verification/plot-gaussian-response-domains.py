"""Plot retained joint boxes from the fixed study; requires optional Matplotlib.

No fitting or production functions are called. Existing output/preview paths
are refused. The saved figure is a conditional mathematical development result.
"""

import argparse
import hashlib
import json
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="new SVG figure")
    parser.add_argument("--preview", type=Path, help="optional new PNG preview")
    args = parser.parse_args()
    targets = [args.output] + ([args.preview] if args.preview else [])
    try:
        if args.output.suffix.lower() != ".svg" or (
            args.preview and args.preview.suffix.lower() != ".png"
        ):
            raise ValueError("output must be SVG and optional preview PNG")
        if any(p.exists() or p.is_symlink() for p in targets):
            raise ValueError("choose fresh figure/preview paths")
        source = Path(__file__).resolve()
        before = {"run": digest(args.run), "plot_source": digest(source)}
        data = json.loads(args.run.read_text())
        if data["format"] != "pictures-to-cad-gaussian-response-domain-study":
            raise ValueError("unsupported study")
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.patches import Patch, Rectangle

        plt.rcParams["svg.hashsalt"] = "gaussian-response-domains-v1"
        plt.rcParams["font.family"] = "DejaVu Sans"
        names = [
            "thin_feasible_offset_line",
            "identity_joint_band",
            "nonlinear_response_joint_band",
        ]
        titles = [
            "An exact feasible line",
            "Identity response; bounded levels",
            "Bounded nonlinear response",
        ]
        colors = {"accepted": "#287B71", "excluded": "#D9DEE5", "unknown": "#F0BD61"}
        figure, axes = plt.subplots(1, 3, figsize=(12, 4), sharex=True, sharey=True)
        selected = []
        for ax, name, title in zip(axes, names, titles):
            rows = [r for r in data["rows"] if r["case"] == name]
            row = max(rows, key=lambda r: r["max_boxes"])
            selected.append(row["index"])
            analysis = row["analysis"]
            for node in analysis["nodes"]:
                if node["status"] == "split":
                    continue
                e0, e1 = map(F, node["box"]["offset"])
                s0, s1 = map(F, node["box"]["sigma"])
                ax.add_patch(
                    Rectangle(
                        (float(e0), float(s0)),
                        float(e1 - e0),
                        float(s1 - s0),
                        facecolor=colors[node["status"]],
                        edgecolor="white",
                        linewidth=0.6,
                    )
                )
            if name == "thin_feasible_offset_line":
                ax.axvline(0, color="#192435", linestyle="--", linewidth=1.4)
            ax.plot(0, 1, "x", color="#192435", markersize=6, markeredgewidth=1.5)
            ax.set_xlim(-0.25, 0.25)
            ax.set_ylim(0.75, 1.25)
            ax.set_aspect("equal")
            ax.set_xlabel("Shared offset (supplied position unit)")
            ax.set_title(
                title + "\n" + f"{analysis['summary']['evaluated_boxes']} evaluated boxes",
                fontsize=10,
            )
        axes[0].set_ylabel("Shared Gaussian sigma (same unit)")
        figure.suptitle("Joint parameter sets: proved boxes and retained uncertainty", fontsize=13)
        handles = [
            Patch(facecolor=colors[k], label=label)
            for k, label in [
                ("accepted", "Proved feasible"),
                ("excluded", "Proved excluded"),
                ("unknown", "Unresolved"),
            ]
        ]
        figure.legend(
            handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.025), frameon=False
        )
        figure.text(
            0.5,
            0.005,
            "Dashed line: exact e=0 alias. Cross: supplied truth (0,1). Conditional model; no camera qualification.",
            ha="center",
            fontsize=8,
        )
        figure.tight_layout(rect=(0, 0.12, 1, 0.91))
        if before != {"run": digest(args.run), "plot_source": digest(source)}:
            raise ValueError("plot inputs changed")
        for p in targets:
            p.parent.mkdir(parents=True, exist_ok=True)
        svg = BytesIO()
        figure.savefig(
            svg,
            format="svg",
            metadata={"Date": None, "Creator": "Pictures to CAD conditional domain study"},
        )
        svg_bytes = b"\n".join(line.rstrip() for line in svg.getvalue().splitlines()) + b"\n"
        with args.output.open("xb") as stream:
            stream.write(svg_bytes)
        if args.preview:
            with args.preview.open("xb") as stream:
                figure.savefig(stream, format="png", dpi=140)
        plt.close(figure)
        print(
            json.dumps(
                {
                    "source_sha256": before,
                    "selected_row_indices": selected,
                    "matplotlib": matplotlib.__version__,
                    "outputs": {str(p): digest(p) for p in targets},
                    "scope": "Retained closed parameter boxes; coordinate hulls are not a feasible Cartesian product.",
                },
                indent=2,
            )
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
