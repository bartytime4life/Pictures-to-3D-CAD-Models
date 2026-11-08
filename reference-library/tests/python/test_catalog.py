"""Catalog integrity: sources.json schema and the files generated from it."""
import csv
import json
import re
import unittest

import _helpers  # noqa: F401  (puts the library root on sys.path)
from _helpers import ROOT

SOURCES = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
REQUIRED = ["id", "category", "title", "url", "type", "level", "use", "limit", "evidence", "checked"]
REPO_FIELDS = ["repository", "license_metadata", "archived", "last_push", "default_branch"]
EVIDENCE = {"page", "page-http-gzip-decoded", "repository-content", "search-content",
            "repository-metadata", "abstract", "discovery-abstract", "metadata"}


class CatalogSchema(unittest.TestCase):
    def test_required_fields_present(self):
        for s in SOURCES:
            for field in REQUIRED:
                self.assertTrue(str(s.get(field, "")).strip(), f"{s.get('id')}: missing {field}")

    def test_ids_and_urls_unique(self):
        self.assertEqual(len({s["id"] for s in SOURCES}), len(SOURCES))
        self.assertEqual(len({s["url"] for s in SOURCES}), len(SOURCES))

    def test_urls_are_https_without_tracking(self):
        for s in SOURCES:
            self.assertTrue(s["url"].startswith("https://"), s["id"])
            self.assertNotRegex(s["url"], r"[?&]utm_[a-z]+=", f"{s['id']} carries a tracking parameter")

    def test_evidence_labels_known_and_dates_iso(self):
        for s in SOURCES:
            self.assertIn(s["evidence"], EVIDENCE, s["id"])
            self.assertRegex(s["checked"], r"^\d{4}-\d{2}-\d{2}$", s["id"])

    def test_github_entries_carry_metadata_matching_url(self):
        repos = [s for s in SOURCES if s["type"] == "GitHub repository"]
        self.assertGreater(len(repos), 0)
        for s in repos:
            for field in REPO_FIELDS:
                self.assertIn(field, s, f"{s['id']}: {field}")
            self.assertTrue(s["url"].lower().endswith("/" + s["repository"].lower()), s["id"])
            self.assertIsInstance(s["archived"], bool)
            self.assertRegex(s["last_push"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class GeneratedFiles(unittest.TestCase):
    """sources.csv, REFERENCES.md and GITHUB.md must be regenerated after catalog edits."""

    def test_csv_matches_json(self):
        with (ROOT / "sources.csv").open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual([r["id"] for r in rows], [s["id"] for s in SOURCES])
        self.assertEqual([r["url"] for r in rows], [s["url"] for s in SOURCES])

    def test_references_lists_every_source(self):
        text = (ROOT / "REFERENCES.md").read_text(encoding="utf-8")
        self.assertIn(f"{len(SOURCES)} resources.", text)
        for s in SOURCES:
            self.assertIn(f"]({s['url']})", text, s["id"])

    def test_github_directory_lists_every_repository(self):
        text = (ROOT / "GITHUB.md").read_text(encoding="utf-8")
        repos = [s for s in SOURCES if s["type"] == "GitHub repository"]
        self.assertEqual(len(re.findall(r"^## \[", text, flags=re.M)), len(repos))
        for s in repos:
            self.assertIn(f"Last push: {s['last_push']}", text, s["id"])


if __name__ == "__main__":
    unittest.main()
