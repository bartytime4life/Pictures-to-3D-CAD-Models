# Flat part shape designer

Open **Shape designer** (`#designer`) to create a flat, constant-thickness part without a photograph or AI. Start from a mounting plate, washer, slotted tab, or blank plate.

1. Choose **Add material** or **Cut through**, then choose a rectangle, rounded rectangle, circle, slot, triangle, or hexagon.
2. Select a shape in the list or click it in the 2D outline. Drag to move it, or enter its center, size, rotation and corner radius. X goes right and Y goes down. Optional snapping moves in 1 mm steps; numeric fields allow finer changes.
3. Set the part thickness. After a 550 ms pause, the app builds the newest design automatically. There is one build at a time; edits during a build queue the newest state. Superseded results are discarded and their files released.
4. Review the CAD preview and its dimensions. Added material must overlap to form one connected part. Cutouts pass through the whole thickness and can open an edge into a notch. Invalid input or a disconnected result preserves the editable design and blocks stale exports.
5. Download **STEP**, **STL**, or **DXF**. STEP and DXF preserve exact lines, circular arcs and circles. STL is a tessellated mesh in millimeters.
6. Choose **Open in flat-part workbench** for scaling, print planning, exports and slicer handoff. You can save that version and record prints in the Flat part Project library. Later changes to the shape composition stay in the designer. See the [snapshot workflow](workflows.md#save-snapshots-and-record-prints).

**Save design** keeps the editable shape composition as `shape-design.json`. **Open design** restores it after validating the complete file. Undo and redo retain up to 40 edit snapshots. In-page navigation retains the draft; reloading does not. Save important designs before closing the app. Replacing a starter is undoable.

A circle's width is its diameter. A slot uses the supplied width and height as its outer bounds. Rounded rectangle corners may be at most half the smaller side. Triangles and six-sided outlines use the entered bounding width and height; a stretched hexagon is not necessarily regular.

## Limits and checks

The designer accepts 1–16 shapes, widths/heights of 0.5–1000 mm, centers within ±1000 mm, rotations within ±180°, thickness of 0.1–500 mm, and a resulting part envelope supported by the existing 0.1–2000 mm CAD workflow. These are application limits, not printability guarantees. Closely touching edges, vanishing features, separating cuts, or overly complex boundaries can be refused by the geometry checks.

`POST /api/designer/build` uses the existing CAD concurrency lock, private temporary job directory, 60-second isolated worker limit and expiry/deletion rules. The worker performs exact solid union and subtraction, recovers the planar lines/arcs/circles, validates a sampled review outline against those boundaries, and delegates extrusion and exports to the existing CAD worker. Additions are joined first; all cuts are subtracted afterward, regardless of list order.

CAD preview uses the returned mesh from that build, not an independent pretend solid. The 2D canvas is an immediate composition view; the 3D preview and exports become current only after the CAD build succeeds. Review the actual dimensions, receiving application units, and physical fit before making.
