# Printer catalog provenance

`printers.json` is a limited factual extraction from
[SoftFever/OrcaSlicer](https://github.com/SoftFever/OrcaSlicer), pinned to
commit `f55615d7488fe570942f5e25548b8ab9b30778d0` and inspected November 8, 2026.
Credit belongs to the OrcaSlicer project and its profile contributors. Profile
names identify the source's configurations; inclusion does not imply an
endorsement by a printer manufacturer.

The upstream repository publishes the
[GNU Affero General Public License, version 3](https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/LICENSE.txt).
Preserve this attribution and consult that upstream license before reusing the
original profiles. This extraction does not copy the upstream program, G-code,
macros, descriptive profile text, filament settings, print recipes, model meshes,
or artwork. The importer is an original implementation in this repository; it
extracts names, numeric dimensions, geometric point lists, nozzle options, and
selected configuration flags with source links. This attribution does not
relicense the upstream source.

Every variant records its exact source URL and all inherited profile URLs.
Inheritance is resolved within each vendor directory, because common profile
names recur across vendors. Only registered, instantiable machine profiles with
verified FFF/FDM technology and usable numeric geometry are admitted. Missing
parents, cycles, invalid coordinates, unknown technology, and missing dimensions
are reported in `skipped_profiles`. At this snapshot, all 1,106 eligible profiles
were imported and none were skipped.

The result contains 429 model groups in 70 manufacturer or profile families.
Some source families are generic/custom configurations, not commercial
manufacturers. There are 411 rectangular, 15 circular, and three polygonal
default beds. Thirty model defaults have nontrivial excluded paths; ten model
groups have variant-specific build dimensions. Counts refer to the pinned
snapshot, not a promise of complete market coverage.

This catalog records what a slicer profile says. It is not a physical test of a
printer. Hardware revisions, firmware, fitted nozzles, added accessories, and
usable build area can differ. Material compatibility, enclosure, heated bed,
automatic leveling, and installed multimaterial equipment are not inferred from
model names, start G-code, filament lists, or purge-tower settings. Unknown
features are explicit `null` values. A profile's multimaterial or chamber-control
flag remains labeled as a configuration flag, not verified installed hardware.

See [the catalog guide](../docs/printer-catalog.md) for the schema and exact
offline reproduction procedure. The application reads the bundled JSON; it
does not contact OrcaSlicer or GitHub at runtime.
