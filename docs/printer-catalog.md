# Printer catalog

The workbench bundles **429 printer model groups with 1,106 nozzle-specific
profiles across 70 manufacturer or profile families**. Examples include Bambu
Lab, Prusa, Creality, Anycubic, Qidi, Sovol, Voron, RatRig, Flashforge, FLSun,
Raise3D, and UltiMaker. Generic/custom source families are included where they
have concrete profile dimensions. This is broad FFF coverage from a pinned
source, not every printer on the market. Resin printers are outside this
catalog's nozzle and extrusion assumptions.

The data is in [printers.json](../data/printers.json). Search by model or family,
then choose the nozzle actually installed. Use custom dimensions when the
catalog does not match the machine. No account, paid service, or internet
connection is needed to read the bundled catalog.

## What is known

Each model groups the exact source variants and records:

- Profile-specified printable width, depth, height, and XY polygon.
- Selected nozzle diameters and any numeric minimum/maximum layer heights.
- Bed shape and the original ordered exclusion paths.
- Printer structure, extruder type, and a few configuration flags when present.
- The exact source URL for the variant and every profile it inherits.

These are source-profile facts, not manufacturer certification or measurements
of the user's hardware. A model's summary uses a 0.4 mm variant when available;
the selected variant's geometry takes precedence. Ten model groups have
different dimensions across variants. For example, an upstream profile may
reserve height and therefore list less Z travel than a marketing specification.

The source has 411 rectangular, 15 circular, and three polygonal default beds.
Thirty defaults include exclusion paths. A circular bed's bounding rectangle
does not make its corners printable. Compound exclusion paths may contain
repeated points; the importer retains their order instead of inventing separate
rectangles. A simple rectangular fit check must report an unknown result for
unsupported bed geometry or exclusions. Refer to [print planning](print-planning.md)
for the distinction between geometric bounds and a validated slicer job.

Enclosure, heated bed, automatic leveling, and installed multimaterial equipment
are explicit unknowns in the catalog. A slicer flag named
`single_extruder_multi_material` is retained as a **profile flag**, not evidence
that an accessory is installed. Material compatibility is not guessed from
printer names or an available generic filament preset. The assistant should
say when a requested fact is missing and direct the user to the machine's
documentation, rather than fill the gap with an unsupported claim.

## JSON contract

The root contains `schema_version`, `source`, `statistics`, `printers`, and
`skipped_profiles`. `source` includes the repository, commit, inspection date,
and upstream license reference.

Each `printers` entry has a stable `id` of the form
`orca/vendor/model-slug`, its `name` and `manufacturer`, `technology: "FFF"`,
`nozzle_diameters_mm`, and `default_nozzle_mm`. Its summary geometry consists of
`bed_shape`, `build_volume: {x_mm, y_mm, z_mm}`, `printable_area_mm`,
`excluded_areas_mm`, and `exclusion_geometry_requires_review`.

`profiles` contains exact variant records with their own geometry, nozzle list,
nullable `min_layer_height_mm` and `max_layer_height_mm`, nullable
`printer_structure`, `extruder_types`, nullable configuration flags, `source_url`,
and `inherited_source_urls`. `excluded_areas_mm` retains the source's combined
ordered path as one entry; it is not guaranteed to be a collection of simple
polygons. A single zero-point placeholder is omitted because it is not an area.

Model feature keys whose facts are unverified have JSON `null`, not `false`.
Consumers must preserve that distinction. Stable IDs come from source family
and model names; source renames can require a future migration. Version the
schema when its meaning changes.

## Reproduce the snapshot

The importer uses Python's standard library and reads a local source checkout.
It never downloads files itself. Obtain the official source using the normal
network policy, then pin it before importing:

```bash
git clone --filter=blob:none --sparse https://github.com/SoftFever/OrcaSlicer.git /tmp/picad-orca-printers
git -C /tmp/picad-orca-printers checkout --detach f55615d7488fe570942f5e25548b8ab9b30778d0
git -C /tmp/picad-orca-printers sparse-checkout set --no-cone '/resources/profiles/*.json' '/resources/profiles/*/machine/*.json' '/LICENSE*'
python3 scripts/import_printers.py /tmp/picad-orca-printers
```

The checkout's source profiles must be clean. The importer checks the commit,
resolves inheritance within each vendor, detects missing or cyclic parents,
handles source coordinate serialization variants, and reports every skipped
eligible profile. It admits only registered instantiable FFF/FDM profiles with
finite, positive nozzle and build dimensions. The current snapshot imports all
1,106 eligible profiles with zero skips. Source G-code, print/filament recipes,
meshes, and artwork are not copied into the catalog.

To update the source, review the upstream changes, explicitly change the pinned
commit and inspection date in [the importer](../scripts/import_printers.py),
regenerate the JSON, review skips and changed bounds, and rerun the importer
regressions. Do not silently update printer facts during app startup.

[Source attribution and license record](../data/PRINTER_SOURCES.md) identifies
OrcaSlicer and its contributors and links the original AGPL v3 license.
