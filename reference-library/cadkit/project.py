"""Scaffold the handbook's minimum project folder (section 4) from the templates."""

from __future__ import annotations

import csv
import re
import shutil
import unicodedata
from datetime import date
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

FOLDERS = {
    "inputs-third-party": "Third-party photographs, models, and listings. Exclude from shared archives unless their terms allow redistribution.",
    "originals": "Your own original photographs and scans. Never overwrite; preprocessing writes copies elsewhere.",
    "preprocessing": "Crops, undistortion, masks, and other derived images, each with the step that produced it.",
    "calibration": "Camera calibration, scale references, homographies, and the transforms between named frames.",
    "measurements": "Instrument readings and the measurement register.",
    "reconstruction": "Raw and cleaned reconstructions. Keep the raw mesh unmodified.",
    "cad": "Editable CAD masters and scripts. They read the project's design-parameters.csv.",
    "drawings": "Dimensioned drawings exported from the CAD master.",
    "print-exports": "Generated print meshes and slicer projects. Disposable build products.",
    "validation": "Coupon and print measurements, acceptance worksheets, and evidence photos.",
}

# template file -> destination folder ("" = project root)
PLACEMENT = {
    "PROJECT-BRIEF.md": "",
    "design-parameters.csv": "",
    "assumptions-register.csv": "",
    "CAPTURE-CHECKLIST.md": "originals",
    "measurement-register.csv": "measurements",
    "validation-results.csv": "validation",
    "PRINT-ACCEPTANCE.md": "validation",
}

MANIFEST_COLUMNS = ("file", "origin", "date", "terms", "redistributable", "sha256", "notes")


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or "project"


def new_project(dest: str | Path, name: str, templates: str | Path | None = None,
                today: date | None = None) -> list[Path]:
    """Create the folder tree and copy templates; returns the created file paths.

    Refuses to write into an existing, non-empty directory.
    """
    if not name or not name.strip():
        raise ValueError("project name must not be empty")
    dest = Path(dest)
    templates = Path(templates) if templates else TEMPLATES
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise FileExistsError(f"{dest} exists and is not an empty directory")
    missing = [t for t in PLACEMENT if not (templates / t).exists()]
    if missing:
        raise FileNotFoundError(f"templates not found in {templates}: {', '.join(missing)}")
    stamp = (today or date.today()).isoformat()
    created: list[Path] = []
    dest.mkdir(parents=True, exist_ok=True)
    for folder, purpose in FOLDERS.items():
        (dest / folder).mkdir()
        readme = dest / folder / "README.md"
        readme.write_text(f"# {folder}\n\n{purpose}\n", encoding="utf-8")
        created.append(readme)
    for template, folder in PLACEMENT.items():
        target = dest / folder / template if folder else dest / template
        shutil.copyfile(templates / template, target)
        created.append(target)
    manifest = dest / "source-manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(MANIFEST_COLUMNS)
        writer.writerow(["EXAMPLE_ONLY", "who made it and where it came from", stamp,
                         "license or permission", "no", "", "Replace this row; hash every input file"])
    created.append(manifest)
    tree = "\n".join(f"- `{folder}/` - {purpose}" for folder, purpose in FOLDERS.items())
    readme = dest / "README.md"
    readme.write_text(
        f"# {name.strip()}\n\n"
        f"Project id: `{slugify(name)}` - created {stamp} with `python3 -m cadkit new-project`.\n\n"
        "Fill in `PROJECT-BRIEF.md` first: purpose, scale declaration, coordinate frame, process, and "
        "acceptance criteria. Every governing value lives in `design-parameters.csv`; scripts and "
        "drawings read it instead of retyping numbers. Record each input with its terms and SHA-256 "
        "hash in `source-manifest.csv`.\n\n"
        "## Folders\n\n"
        f"{tree}\n\n"
        "## Evidence classes\n\n"
        "Label every dimension measured, image-derived, inferred, or unknown. A derived value takes "
        "the weakest class of its inputs. Blank values mean unknown, never zero.\n",
        encoding="utf-8",
    )
    created.append(readme)
    return created
