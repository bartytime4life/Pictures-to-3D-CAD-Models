"""Plot all wall-localization group maxima; requires a separate Matplotlib environment."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.preview is not None and args.preview.exists():
        parser.error("choose new figure paths")
    result = json.loads((args.run / "results.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), sharey=True)
    observations = [("point", "Point observations"), ("uniform_pixel_mean", "Uniform pixel means")]
    for ax, (kind, title) in zip(axes, observations):
        groups = sorted((g for g in result["summary"] if g["observation"] == kind), key=lambda g: g["wall_level"])
        positions = np.arange(len(groups))
        for label, shift, color, legend in [("baseline", -.18, "#79818e", "Published baseline"),
                                             ("candidate", .18, "#176da6", "Local candidate")]:
            values = [g[label + "_maximum_absolute_error_px"] for g in groups]
            bars = ax.bar(positions + shift, values, width=.34, color=color, label=legend)
            ax.bar_label(bars, labels=[f"{v:.3f}" for v in values], padding=4, fontsize=7, rotation=90)
        ax.set_xticks(positions, [f"{g['wall_level']:g}" for g in groups])
        ax.set_xlabel("Wall level (linear light, 0–255)")
        ax.set_title(title, loc="left", weight="bold", fontsize=11)
        ax.set_ylim(0, 3.6)
        ax.grid(axis="y", color="#e0e4e8", linewidth=.6)
        ax.set_axisbelow(True)
        ax.spines[["right", "top"]].set_visible(False)
    axes[0].set_ylabel("Maximum post-wall boundary error (pixels)")
    axes[0].legend(loc="upper left", fontsize=8, frameon=False)
    fig.suptitle("Local wall-fit changes help some cases; large errors remain", x=.07, ha="left", weight="bold", fontsize=12)
    fig.text(.07, .035, "16 scenes/group; all 192 pairs retained. Errors cover selected central-left points, including unchanged seeds.\n"
             "Same initial traces and supplied cameras. This is development evidence, not physical accuracy or a release pass.", fontsize=8)
    fig.subplots_adjust(left=.07, right=.99, top=.82, bottom=.23, wspace=.08)
    fig.savefig(args.output, format="svg", metadata={"Date": None})
    if args.preview:
        fig.savefig(args.preview, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
