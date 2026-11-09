"""Documentation accuracy: the prose must agree with the data, the code, and the files.

Each test turns a factual claim in the documentation into a check, so a stale
count, a broken relative link, or a worked number that drifts from the
calculation script fails the suite instead of reaching a reader.
"""
import json
import math
import os
import re
import unittest
from pathlib import Path

import _helpers  # noqa: F401
from _helpers import ROOT, GOLDEN

SOURCES = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
REPOS = [s for s in SOURCES if s["type"] == "GitHub repository"]
LIB = json.loads((ROOT / "library.json").read_text(encoding="utf-8"))
CALCULATORS = json.loads((ROOT / "assets/data/calculators.json").read_text(encoding="utf-8"))
ROUTES = json.loads((ROOT / "assets/data/routes.json").read_text(encoding="utf-8"))
HANDBOOK = (ROOT / "HANDBOOK.md").read_text(encoding="utf-8")
GOLD = json.loads(GOLDEN.read_text(encoding="utf-8"))
SECTIONS = {int(m.group(1)): m.group(2) for m in re.finditer(r"^## (\d+)\. (.+)$", HANDBOOK, flags=re.M)}

MARKDOWN = [ROOT / "README.md", ROOT / "CHANGELOG.md", ROOT / "CONTRIBUTING.md",
            ROOT / "HANDBOOK.md", ROOT / "BUILD.md", ROOT / "VERIFICATION.md", ROOT / "RESEARCH-NOTES.md",
            ROOT / "examples/README.md", ROOT / "cadkit/README.md"]


def links(path: Path):
    """(target, is_image) for every Markdown link outside fenced code blocks."""
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)  # inline code shows syntax, not links
    for m in re.finditer(r"(!?)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text):
        yield m.group(2), bool(m.group(1))


class Counts(unittest.TestCase):
    def test_readme_counts_match_data(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"{len(SOURCES)} annotated sources", text)
        self.assertIn(f"{len(REPOS)} GitHub repository records", text)
        self.assertIn(f"{len(CALCULATORS)} calculators", text)
        self.assertIn(f"Revision {LIB['revision']}", text)
        self.assertIn(f"{len(SECTIONS)}-chapter handbook", text)
        explanatory = [f for f in (ROOT / "assets/figures").glob("*.svg") if f.stem != "banner"]
        self.assertIn(f"{len(explanatory)} explanatory figures", text)

    def test_changelog_command_count_matches_cli(self):
        from cadkit import cli
        commands = cli.build_parser()._subparsers._group_actions[0].choices
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"with {len(commands)} commands", changelog)

    # record-verification.py runs this suite before it rewrites verification.json, then
    # re-runs these two tests afterwards; RECORDING skips them during the first pass.
    RECORDING = os.environ.get("CAD_RECORDING_VERIFICATION") == "1"

    @unittest.skipIf(RECORDING, "verification.json is being rewritten")
    def test_verification_record_matches_data(self):
        record = json.loads((ROOT / "verification.json").read_text(encoding="utf-8"))
        self.assertEqual(record["revision"], LIB["revision"])
        self.assertEqual(record["source_records"], len(SOURCES))
        self.assertEqual(record["github_repositories"], len(REPOS))
        self.assertEqual(record["calculators"], len(CALCULATORS))
        text = (ROOT / "VERIFICATION.md").read_text(encoding="utf-8")
        self.assertIn(f"Revision {LIB['revision']}", text)
        self.assertIn(f"{len(SOURCES)} entries", text)
        self.assertIn(f"{len(REPOS)} GitHub repository", text)
        self.assertIn(f"{record['pdf_pages']} pages", text)
        # The prose counts of the last recorded run must be the recorded ones.
        self.assertIn(f"{record['python_tests']['ran']} Python tests", text)
        self.assertIn(f"{record['node_tests']['passed']} Node test groups", text)
        self.assertIn(f"{record['browser_checks']['assertions']} assertions", text)
        self.assertIn(f"`{record['browser_checks'].get('transport', 'file')}`", text)
        plate = record["openscad_plate_checks"]
        if isinstance(plate, dict):
            self.assertEqual(plate["rows"], plate["passed"])
            self.assertIn(f"all {plate['rows']} checks", text)

    @unittest.skipIf(RECORDING, "verification.json is being rewritten")
    def test_pdf_page_count_matches_record(self):
        pdf = ROOT / "output/pdf/pictures-to-printable-cad.pdf"
        record = json.loads((ROOT / "verification.json").read_text(encoding="utf-8"))
        pages = len(re.findall(rb"/Type /Page\b(?!s)", pdf.read_bytes()))
        self.assertEqual(pages, record["pdf_pages"])

    def test_revision_is_consistent(self):
        self.assertIn(f"**Revision {LIB['revision']}, {LIB['date_label']}.**", HANDBOOK)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        first = re.search(r"^## (.+)$", changelog, flags=re.M).group(1)
        self.assertIn(f"Revision {LIB['revision']}", first)


class Links(unittest.TestCase):
    def test_relative_links_resolve(self):
        for doc in MARKDOWN:
            for target, _ in links(doc):
                if re.match(r"^(https?:|mailto:|#)", target):
                    continue
                path = (doc.parent / target.split("#")[0]).resolve()
                self.assertTrue(path.exists(), f"{doc.relative_to(ROOT)} links to missing {target}")

    def test_external_handbook_links_are_catalogued(self):
        catalog = {s["url"] for s in SOURCES}
        for doc in (ROOT / "HANDBOOK.md", ROOT / "RESEARCH-NOTES.md"):
            for target, _ in links(doc):
                if target.startswith("http"):
                    self.assertIn(target, catalog, f"{doc.name}: {target} is not in sources.json")

    def test_every_figure_is_used(self):
        used = HANDBOOK + (ROOT / "README.md").read_text(encoding="utf-8") \
            + (ROOT / "scripts/build-library.mjs").read_text(encoding="utf-8") \
            + (ROOT / "scripts/make-pdf.py").read_text(encoding="utf-8")
        for svg in (ROOT / "assets/figures").glob("*.svg"):
            self.assertIn(svg.stem, used, f"{svg.name} is never shown")

    def test_catalog_chart_is_current(self):
        svg = (ROOT / "assets/figures/catalog-composition.svg").read_text(encoding="utf-8")
        self.assertIn(f"<title id=\"catalog-composition-title\">{len(SOURCES)} catalog sources", svg)


class WorkedNumbers(unittest.TestCase):
    """The handbook's synthetic examples must state what calculate.py computes."""

    def assertStated(self, phrase):
        self.assertIn(phrase, HANDBOOK)

    def test_scale_and_uncertainty(self):
        self.assertStated(f"scale is {GOLD['scale_mm_per_pixel']:.5f} mm/pixel")
        self.assertStated(f"is {GOLD['feature_length_mm']:.2f} mm under the stated planar assumptions")
        self.assertStated(f"`uL ≈ {GOLD['standard_uncertainty_mm_independent_small_error_model']:.3f} mm`")

    def test_tessellation(self):
        self.assertStated(f"at least {GOLD['minimum_circle_segments']} segments are needed")

    def test_calibration_check(self):
        self.assertStated(f"appears {GOLD['calibration_check_squat_percent']:g}% too squat")
        self.assertStated(f"about {GOLD['calibration_check_vertical_stretch_percent']:.1f}% relative to horizontally")

    def test_depth_and_camera(self):
        self.assertStated(f"the factor is {GOLD['off_plane_depth_factor']:g}")
        self.assertStated(f"is about {GOLD['off_plane_corrected_size_mm']:.1f} mm")
        lo, hi = GOLD["off_plane_factor_range"]
        self.assertStated(f"from about {lo:.2f} to {hi:.2f}")
        self.assertStated(f"`f_px ≈ {round(GOLD['camera_focal_length_px'])}`")
        self.assertStated(f"about {round(GOLD['camera_distance_mm'])} mm from the camera")
        self.assertTrue(math.isclose(math.hypot(36, 24), 43.27, abs_tol=0.005))
        self.assertStated("43.27 mm full-frame diagonal")

    def test_label_rounding_and_coating(self):
        self.assertStated(f"±{GOLD['label_rounding_half_interval_mm']:.3f} mm")
        self.assertStated(f"about {GOLD['label_rounding_standard_uncertainty_mm']:.3f} mm")
        self.assertStated(f"removes {GOLD['coated_slot_width_loss_mm']:.2f} mm of slot width")

    def test_gears(self):
        d1, d2 = GOLD["gear_pitch_diameters_mm"]
        self.assertStated(f"pitch diameters {d1:g} and {d2:g} mm, nominal center distance {GOLD['gear_nominal_center_distance_mm']:g} mm")
        self.assertStated(f"output speed of {GOLD['gear_output_input_speed_ratio']:g} times the input speed".replace("-", "−"))


class ToolkitData(unittest.TestCase):
    def test_calculators_reference_real_sections(self):
        self.assertEqual(len({c["id"] for c in CALCULATORS}), len(CALCULATORS))
        for c in CALCULATORS:
            self.assertIn(c["section"], SECTIONS, c["id"])
            self.assertTrue(c["inputs"] and c["formula"] and c["note"], c["id"])

    def test_route_workflows_point_at_the_right_chapters(self):
        calc_ids = {c["id"] for c in CALCULATORS}
        source_ids = {s["id"] for s in SOURCES}
        for key, wf in ROUTES["workflows"].items():
            self.assertIn(wf["section"], SECTIONS, key)
            if key in "ABCDE":
                self.assertTrue(SECTIONS[wf["section"]].startswith(f"Workflow {key}:"), key)
            self.assertTrue(set(wf["calculators"]) <= calc_ids, key)
        for rule in list(ROUTES["by_input"].values()) + list(ROUTES["by_goal"].values()):
            self.assertTrue(set(rule["sources"]) <= source_ids)

    def test_toolkit_chapter_names_every_cli_command(self):
        from cadkit import cli
        commands = set(cli.build_parser()._subparsers._group_actions[0].choices) - {"version"}
        chapter = HANDBOOK[HANDBOOK.index("## 23. Companion toolkit"):]
        for name in commands:
            self.assertIn(f"`{name}`", chapter, name)
        readme = (ROOT / "cadkit/README.md").read_text(encoding="utf-8")
        for name in commands:
            self.assertIn(f"`{name}`", readme, name)


if __name__ == "__main__":
    unittest.main()
