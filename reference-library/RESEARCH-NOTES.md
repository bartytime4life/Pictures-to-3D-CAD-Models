# Research map and search record

Prepared November 8, 2026. This is a curated reference search, not a systematic review or a software benchmark.

## What was searched

Public web searches covered photo capture, camera calibration, planar rectification, structure from motion, mesh reconstruction, mesh-to-CAD conversion, CAD drawings, NURBS and differential geometry, additive-manufacturing inspection, and scientific 3D datasets. Official project documentation, author pages, university materials, specifications, and original research were preferred.

GitHub's connected tools were used for repository discovery and live metadata checks. The directory records the default branch, last push, archived flag, and API-reported license identifier. Those fields do not establish build quality, security, release stability, or that every bundled component has the same license. `NOASSERTION` means the API did not assign a definitive SPDX identifier; it does not mean unrestricted use.

SciSpace was searched with two questions:

- Which methods reconstruct editable parametric CAD models from photographs, sketches, or 3D point clouds, and how is dimensional accuracy evaluated?
- How accurate is close-range photogrammetry for reverse engineering physical objects for additive manufacturing compared with measured reference geometry?

Eight relevant records were selected for the interactive SciSpace table and the persistent catalog. The full bibliographic record and abstract of Turek and colleagues' 2024 paper were fetched. The other selected records were reviewed at search-excerpt level. No paper was treated as fully reviewed merely because it appeared in the search.

The Life Sciences Literature Entrez helper searched PubMed for photogrammetry combined with printing/reverse engineering, then a bounded anatomy-focused query for 2015–2024. Selected bibliographic identifiers were checked with summary/fetch calls. A spectacles paper is retained as a bibliographic lead only. The guide makes no clinical efficacy claims.

Google Drive was searched for existing CAD material. A matching PDF was inspected and found to concern an unrelated building project, so its contents were excluded. Other unrelated results were not used. No private Drive text, file identifiers, or personal drawing details are included in this package, and no Drive document was changed or created.

The Data and Product Design routing skills were consulted. This task concerns engineering reference writing and a source catalog, not a warehouse analysis or a software-interface redesign. Life Sciences Databases' genomic workflow was reviewed and was not forced into an unrelated CAD problem. Relevant scientific 3D repositories were instead researched through their official public pages.

## A reading order that answers practical questions

| Question | Read first | Why it matters |
| --- | --- | --- |
| How do I photograph an object usefully? | Meshroom capture guide; COLMAP tutorial | Coverage, texture, and viewpoint geometry precede reconstruction settings |
| How do I trace a measurable part? | FreeCAD scaled-image tutorial; OpenCV calibration/homography | Establish the plane and scale before fitting an outline |
| Why is my converted STL hard to edit? | Fusion mesh conversion; McNeel reverse engineering | Mesh faces, analytic surfaces, and feature history are different representations |
| How do I know the geometry is right? | CloudCompare distances; NIST test artifact | Alignment, independent references, and feature-specific inspection matter |
| How do I learn the mathematics? | Oxford multi-view geometry; MIT hyperbook; CMU DDG | Study projection, curve/surface geometry, and discrete surfaces in that order |
| Can AI recover a useful CAD model? | DeepCAD and BrepGen author/code pages; then recent leads | Separate representation research from real-photo metrology |
| How do images of anatomy become printable? | 3D Slicer segmentation and training | Volumetric images and exterior photographs require different workflows |
| Which way is up, and what unit is this file in? | glTF 2.0 specification; 3MF core specification | Exchange formats differ in axes and units; convert explicitly on import |
| How do I re-pose or adapt a sculpted subject? | Blender posing; Blender sculpting | Pose changes need an armature or sculpting, not a rigid transform |
| How should I hollow or split a large print? | Formlabs hollowing guide; PrusaSlicer cut tool | Drain holes and connectors need a fit test in the real material |
| How uncertain is a rounded published dimension? | JCGM 100 (GUM), section 4.3.7 | A bound of ±a gives standard uncertainty a/√3 for rounding alone |
| Can I share or adapt this model or image? | Creative Commons license types; the asset's own terms | File licenses and character or trademark rights are separate questions |

## How to interpret the research

Turek and colleagues' [2024 CAD accuracy study](https://scispace.com/papers/analysis-of-the-accuracy-of-cad-modeling-in-engineering-and-36nxm62vq6) is particularly relevant because its abstract distinguishes measurement data and subsequent CAD modeling. The reported geometry-specific deviations are not transferred to a phone camera or this user's printer. Use the study to design separate checks for acquisition and remodeling.

The older artifact-reproduction and small-object photogrammetry studies in the catalog provide workflow precedents. They do not establish a universal tolerance. Surface preparation, object size, camera calibration, acquisition geometry, measurement reference, and post-processing can all change the result. A published percentage should never be copied without its denominator and test conditions.

DeepCAD is an operation-sequence research baseline; BrepGen addresses B-rep generation. Neither project's presence in a tool directory establishes one-click reconstruction of an arbitrary photographed part. Recent CADFit, Image2CADSeq, and RealCAD records are useful discovery leads. Their full methods, publication status, implementation availability, and benchmarks require further verification before adopting them.

## Evaluate papers with this worksheet

- Input modality: real photos, synthetic renders, RGB-D, CT, mesh, or point cloud?
- Calibration: camera model, physical scale, coordinate frames, and control targets?
- Object set: number, materials, sizes, topology, and functional features?
- Output: mesh, implicit field, B-rep, editable operation sequence, or assembly?
- Ground truth: independent metrology, existing CAD, or another unqualified scan?
- Alignment: rigid, similarity, or deformable; were dimensions normalized away?
- Metrics: physical units, regional errors, quantiles, invalid-model rate, and editability?
- Selection: all attempts or only successful reconstructions; exclusions explained?
- Reproducibility: code, exact versions, dataset split, licenses, and compute cost?
- Printing: was a part actually fabricated and measured, or only rendered/sliced?

## Retrieval limitations

- MorphoSource's live catalog returned an access-denied page. Its official repository description supports the directory entry; no individual media record was inspected.
- Some PubMed pages returned only a minimal shell. Entrez was used for identifiers and metadata; the catalog distinguishes bibliographic-only entries.
- The direct MDPI landing page for the 2024 study returned HTTP 429. Its SciSpace record supplied the abstract and bibliographic data; no repeated attempts were made to bypass the limit.
- The CVF landing page for Structure-from-Motion Revisited returned HTTP 403 after discovery. Its search-index abstract and COLMAP's documentation provided bounded context.
- An old guessed Meshroom requirements URL returned 404 and was omitted. Consult the current project documentation before installation.
- KHK's page initially appeared as compressed binary in the web parser. A normal public HTTP retrieval with gzip decoding exposed the technical reference; the catalog records this alternate read.
- An incorrect candidate repository path for BrepGen failed. The author-linked `samxuxiang/BrepGen` repository was found and checked instead.
- Revision 2: two guessed Formlabs hollowing URLs returned 404, and a guessed Prusa article number led to an unrelated hotend guide. A web search found the current Formlabs hollowing article, whose page text was then read. A guessed Blender sculpting subpage returned 404; the sculpting index page was used instead.

## Revision 2 additions

Revision 2, prepared November 8, 2026, extends the handbook with generic methods prompted by a review of a hybrid project: a sculpted subject combined with a precisely held purchased object. Project-specific data is not included. The new material is engineering synthesis; its worked numbers are synthetic and reproduced by `examples/calculate.py`.

Seven sources were added after their page text was read on November 8, 2026:

- The glTF 2.0 specification, section 3.4 on coordinate system and units.
- The Blender manual's posing introduction and sculpting index.
- PrusaSlicer's cut-tool article, which is filed under a legacy release.
- The Formlabs hollowing article.
- Creative Commons' license overview.
- JCGM 100:2008 (GUM), whose section 4.3.7 rectangular-distribution text was extracted from the BIPM PDF.

The existing 3MF core specification entry was reused for the 3MF unit default. No new software was installed, run, or benchmarked.

## Revision 3 maintenance

Revision 3, prepared November 8, 2026, added no new sources and changed no review depths. It made three maintenance checks:

- **Repository metadata:** `scripts/refresh-github.mjs` re-read all 21 repositories from the public GitHub API. Four had pushed since the Revision 2 snapshot (COLMAP, FreeCAD, CadQuery, and OrcaSlicer); only their `last_push` values changed. No repository was archived, renamed, or relicensed.
- **Link availability:** `scripts/check-links.mjs` requested every catalog URL. In the first run (21:03 UTC), 84 of 86 responded normally. The two Smithsonian pages returned HTTP 403 to the automated client, which is a refusal of automated access, not evidence that the pages are gone. In a second run about half an hour later, the whole open3d.org site timed out; a third run reached it again. Availability varies from run to run, and `verification.json` records the most recent one. Every external link in the handbook and these notes is also a catalog entry.
- **Tracking parameters:** the eight SciSpace research URLs carried `utm_source` and `utm_medium` parameters added by the discovery tool. They were removed; the pages are unchanged.

A link check shows that a server answered at the time of the check. It does not re-review a page's content or confirm that the text supporting an annotation is still there.

## November 9 research update

A focused SciSpace query asked: “How do metrology studies of close-range photogrammetry and reverse-engineered CAD distinguish alignment error, scale uncertainty, reconstruction error, and independent check measurements?” with open-access and eight-result filters. The eight returned excerpts were screened. The full bibliographic record and abstract of di Filippo and colleagues' 2022 study were fetched, then selected publisher-PDF sections 2–4 were read. The paper's tie-point analysis does not include dense image-matching uncertainty; no published tolerance was transferred to this project.

[JCGM 106:2012](https://www.bipm.org/documents/20126/2071204/JCGM_106_2012_E.pdf/fe9537d2-e7d7-e146-5abb-2649c3450b25), section 8.3, was read from BIPM's official PDF for acceptance decisions near tolerance limits. The handbook's numerical guard-band example is synthetic. It illustrates a declared decision rule, with no physical result or standards certification implied.

A reusable independent-check worksheet and CSV register make the evaluation sequence concrete: reserve checks, freeze the evaluated revision, and retire a check from independent status if it guides a correction.

Both additions are marked page-content checked, with the selected sections stated in their catalog limitations. Existing review depths and dates were not promoted. The Life Sciences Literature PMC metadata skill was inspected for relevance; no biomedical article lookup was needed for this metrology question. No new private Drive search, software installation, or reconstruction experiment was performed for this update.

## Refreshing the library

Keep the conceptual explanations stable and refresh software versions, dependency requirements, licenses, and repository status before installation. For a future research update, record the query, date, selected sources, review depth, and reasons for exclusions. Add substantive findings only after reading enough of the source to support them. The `sources.json` and `sources.csv` files provide the structured starting point.
