"""Offline guides expose only curated regular files and preserve source bytes."""

import hashlib
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import documentation as docs


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(docs.router)
    with TestClient(app) as instance:
        yield instance


def test_guide_and_download_match_the_checkout_bytes(client, tmp_path, monkeypatch):
    raw = b"# Capture\r\n\r\nMeasure the reference before applying scale.\r\n"
    (tmp_path / "capture-guide.md").write_bytes(raw)
    monkeypatch.setattr(docs, "DOCS_ROOT", tmp_path)
    document = client.get("/api/docs/capture")
    assert document.status_code == 200
    assert document.json() == {
        "slug": "capture", "title": "Capture guide", "content": raw.decode(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    assert document.headers["x-content-type-options"] == "nosniff"
    download = client.get("/api/docs/capture/download")
    assert download.content == raw
    assert download.headers["content-disposition"] == 'attachment; filename="capture.md"'
    assert download.headers["content-type"].startswith("text/markdown")


def test_index_is_a_curated_guide_list(client):
    result = client.get("/api/docs")
    assert result.status_code == 200
    assert {item["slug"] for item in result.json()["documents"]} == set(docs.DOCUMENTS)
    assert "content" not in result.json()["documents"][0]


@pytest.mark.parametrize("slug", ["README.md", "../README.md", "%2e%2e%2fREADME.md", "%00", ".env"])
def test_non_curated_names_never_expose_files(client, slug):
    assert client.get(f"/api/docs/{slug}").status_code == 404


@pytest.mark.parametrize("kind", ["missing", "symlink", "directory", "fifo", "oversized", "bad_utf8"])
def test_unavailable_or_special_documents_are_rejected(client, tmp_path, monkeypatch, kind):
    monkeypatch.setattr(docs, "DOCS_ROOT", tmp_path)
    path = tmp_path / "capture-guide.md"
    if kind == "symlink":
        private = tmp_path / "private.txt"
        private.write_text("private data")
        path.symlink_to(private)
    elif kind == "directory":
        path.mkdir()
    elif kind == "fifo":
        if not hasattr(os, "mkfifo"):
            pytest.skip("No FIFO support on this platform")
        os.mkfifo(path)
    elif kind == "oversized":
        path.write_bytes(b"x" * (docs.MAX_DOCUMENT_BYTES + 1))
    elif kind == "bad_utf8":
        path.write_bytes(b"\xff\xfe")
    assert client.get("/api/docs/capture").status_code == 404
    assert client.get("/api/docs/capture/download").status_code == 404


def test_all_curated_guides_exist_in_this_checkout():
    for slug in docs.DOCUMENTS:
        result = docs.read_document(slug)
        assert result["content"].startswith("# ")
