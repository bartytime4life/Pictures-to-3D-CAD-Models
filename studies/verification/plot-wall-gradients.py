"""Plot synthetic ambiguity and known-tone errors; requires matplotlib."""

import argparse
import csv
import io
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new SVG file")
    parser.add_argument("--preview", type=Path, help="optional new PNG file")
    args = parser.parse_args()
    if args.output.exists() or args.preview is not None and args.preview.exists():
        parser.error("choose new output paths")
    with (args.run / "image-fits.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans", "svg.fonttype": "none",
                         "svg.hashsalt": "bounded-wall-gradients-v1", "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), gridspec_kw={"width_ratios": [1.1, 1]})
    t = np.linspace(-4, 5, 301)
    light = 48 + 188 * np.asarray([0.5 * math.erfc(-v / math.sqrt(2)) for v in t])
    ax = axes[0]
    ax.plot(t, light, color="#147d88", linewidth=4, label="Wall matches top; silhouette 0 px")
    ax.plot(t, light, color="#be7424", linewidth=2, linestyle="--", label="Wall matches paper; silhouette 1.5 px")
    ax.axvline(0, color="#147d88", linewidth=1.3, alpha=0.65)
    ax.axvline(1.5, color="#be7424", linewidth=1.3, alpha=0.65)
    ax.set(title="Same light field, different silhouette", xlabel="Position along supplied normal (px)",
           ylabel="Linear light level (0–255)", ylim=(25, 255))
    ax.legend(loc="lower right", fontsize=9, frameon=True, facecolor="white", edgecolor="none", framealpha=1)
    ax.text(0.02, 0.96, "Known wall width 1.5 px; Gaussian σ = 1 px", transform=ax.transAxes,
            va="top", fontsize=9)
    conditions = ["flat", "top_rises", "both_slopes"]
    for delta, stage, label, color in [(-0.18, "point_known_sigma", "Pixel centres", "#147d88"),
                                      (0.18, "aperture_known_sigma", "Uniform pixel means", "#be7424")]:
        errors = [max(abs(float(r["offset_px"])) for r in rows if r["method"] == "true_fixed_wall_tone"
                      and r["stage"] == stage and r["condition"] == condition) for condition in conditions]
        bars = axes[1].bar(np.arange(3) + delta, errors, width=0.34, label=label, color=color)
        for bar, value in zip(bars, errors):
            axes[1].annotate(f"{value:.3f}", (bar.get_x() + bar.get_width() / 2, value),
                             ha="center", va="bottom", fontsize=9, xytext=(0, 3), textcoords="offset points")
    axes[1].set(title="Known wall tone does not remove lighting bias", ylabel="Maximum absolute fitted error (px)",
                xticks=np.arange(3), xticklabels=["Flat light", "Top gradient", "Top + paper gradients"], ylim=(0, 0.125))
    axes[1].legend(frameon=False, fontsize=9)
    axes[1].tick_params(axis="x", labelsize=9)
    for ax in axes:
        ax.grid(axis="y", color="#d7dee1", linewidth=0.5)
        ax.set_axisbelow(True)
    fig.text(0.5, 0.015, "Synthetic local profiles; supplied true band and optical blur. These are fixture errors, not camera accuracy bounds.",
             ha="center", fontsize=9, color="#39454d")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    buffer = io.StringIO()
    fig.savefig(buffer, format="svg", metadata={"Date": None})
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write("\n".join(line.rstrip() for line in buffer.getvalue().splitlines()) + "\n")
    if args.preview is not None:
        fig.savefig(args.preview, format="png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
