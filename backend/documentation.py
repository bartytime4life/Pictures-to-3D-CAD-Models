"""Read-only, curated project guides for the local knowledge studio."""

import hashlib
import os
import stat
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"
MAX_DOCUMENT_BYTES = 1024 * 1024
DOCUMENTS = {
    "shape-designer": ("Flat part shape designer", "shape-designer.md"),
    "creative-tools": ("Creative tools and local AI", "creative-tools.md"),
    "getting-started": ("Getting started", "getting-started.md"),
    "workflows": ("Workflow guide", "workflows.md"),
    "science": ("Science and measurement", "science.md"),
    "troubleshooting": ("Troubleshooting", "troubleshooting.md"),
    "architecture": ("Project architecture", "architecture.md"),
    "exports": ("Exports and dimensions", "exports.md"),
    "capture": ("Capture guide", "capture-guide.md"),
    "slicers": ("Slicer handoffs", "slicers.md"),
    "relief": ("Relief and lithophanes", "relief.md"),
    "development": ("Development guide", "development.md"),
}
router = APIRouter(prefix="/api/docs", tags=["documentation"])
HEADERS = {"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"}


def read_document(slug: str) -> dict[str, str]:
    """Never accept filesystem paths or follow a document symlink/FIFO."""
    if slug not in DOCUMENTS:
        raise HTTPException(404, "Guide not found.")
    title, filename = DOCUMENTS[slug]
    descriptor = None
    try:
        target = DOCS_ROOT / filename
        # lstat protects platforms without O_NOFOLLOW; open/fstat handle replacement
        # and special files without blocking a local-server worker.
        if not stat.S_ISREG(target.lstat().st_mode):
            raise OSError("Guide is not a regular file")
        descriptor = os.open(
            target,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        )
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("Guide is not a regular file")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = None
            data = source.read(MAX_DOCUMENT_BYTES + 1)
        if len(data) > MAX_DOCUMENT_BYTES:
            raise ValueError("Guide is too large")
        content = data.decode("utf-8")
    except (OSError, ValueError, UnicodeError):
        raise HTTPException(404, "Guide is unavailable in this checkout.") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return {
        "slug": slug,
        "title": title,
        "content": content,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


@router.get("")
def list_documents():
    return {"documents": [{"slug": slug, "title": item[0]} for slug, item in DOCUMENTS.items()]}


@router.get("/{slug}/download")
def download_document(slug: str):
    document = read_document(slug)
    return Response(
        document["content"],
        media_type="text/markdown",
        headers={**HEADERS, "Content-Disposition": f'attachment; filename="{slug}.md"'},
    )


@router.get("/{slug}")
def get_document(slug: str, response: Response):
    response.headers.update(HEADERS)
    return read_document(slug)
