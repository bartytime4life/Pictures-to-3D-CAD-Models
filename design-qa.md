# Design QA — option 2

Review date: November 8, 2026 (America/Chicago).

**Findings**

The original workbench was compared with the selected option 2 reference in paired full-view and native-density control captures. The current follow-up adds the user-requested design, printing, and local-assistant controls while retaining the same main workbench composition; its verification is recorded below.

## Evidence and comparison conditions

- Source visual truth: [selected design](docs/images/design-reference.png), the second displayed concept selected by the user; 1487 × 1058 pixels.
- Browser-rendered implementation: [desktop](docs/images/workbench.png), 1488 × 1238 pixels, CSS viewport 1488 × 1058, device scale factor 1.
- State: supplied sample successfully traced and built; 80 mm reference width, 4 mm thickness, standard outline detail, Scale workflow, no dialog open.
- [Paired full-view comparison](docs/images/design-comparison.png): both source and implementation displayed at half size in the same browser capture. The source's one-pixel narrower native width is retained and is not treated as a visual defect.
- [Paired control comparison](docs/images/design-comparison-controls.png): source and implementation dimension controls and footer at native pixel density, cropped through browser layout without modifying either original image.
- [Mobile](docs/images/workbench-mobile.png): CSS viewport 390 × 844, device scale factor 1, full document capture 390 × 1615. Vertical scrolling is intentional; horizontal overflow is absent. The guide button retains keyboard focus in this capture.
- Chromium rendered the actual source image, contour canvas, and CAD mesh. The test waits for the model's real `onAfterRender` readiness marker before capturing. The 3D scene is not a screenshot placeholder.

## Required fidelity surfaces

| Surface | Assessment |
| --- | --- |
| Fonts and typography | Locally bundled Inter Variable and JetBrains Mono Variable reproduce the reference's product/technical hierarchy. Desktop brand, project, panel headings, numerical fields, and footer were enlarged after the first comparison. Mobile helper text was increased to 11 px to remain readable. No external font request is required. |
| Spacing and layout rhythm | Equal source/model panels, header, four-stage workflow, horizontal dimension controls, and bottom summary follow the selected composition. The original footer fit in 1058 px. The current collapsed Design & print and Local AI panels, plus review notes, extend the document to 1238 px. Vertical scrolling is intentional; main dimensions and export controls retain their position. Mobile panels stack and all core controls remain reachable. |
| Colors and tokens | Charcoal surfaces, cyan outline and active stage, restrained dividers, and the blue primary action are retained. The primary action intentionally uses darker blue `#0078b4`, giving approximately 4.83:1 contrast with white text. Flat product surfaces replace decorative raster gradients. |
| Image quality and asset fidelity | A generated source photograph is traced through the real backend. The original release used a generated brushed-metal texture for cosmetic shading. The current viewer uses the selected solid color and an approximate filament finish on the actual CAD mesh. The floor and grid were darkened; lighting, framing, and camera angle were refined. Phosphor icons supply the standard UI iconography. |
| Copy and content | The main workflow and action hierarchy match the reference. “Reference width” explicitly describes the supported calibration. “Scaled dimensions” avoids presenting user-supplied scale as an independent measurement. Sample labeling, upload handling, stale results, and export units provide essential product context. |

## Comparison history

1. **Initial rendered review — blocked.** [Initial capture](docs/images/workbench-initial.png), 1488 × 1096 for a 1488 × 1058 viewport. P2: footer below the intended frame, undersized desktop typography, low-contrast primary action, overly pale/flat model material, and a lighter-than-reference floor. The source canvas also showed an unnecessary background boundary.
2. **First refinement.** [Material/layout capture](docs/images/workbench-material-refinement.png). Enlarged typography, darker compliant primary blue, white source background, removal of redundant STL guidance from the main workbench, and reduced panel height corrected the layout and contrast issues. A generated metal texture, revised lighting, and darker floor corrected the material appearance. Remaining P2: the model occupied too little of the CAD viewport.
3. **Original final desktop comparison — passed.** Both paired comparisons above record that release. Revised isometric orientation and fit margins increased model prominence without changing its vertices, and grid opacity was reduced. The current desktop link includes the later optional controls.
4. **Mobile refinement — passed.** Helper text that was too small was increased to 11 px. The affected keyboard/accessibility/mobile browser test passed again; the final mobile image above records the revised layout.

## Functional and accessibility evidence

The original six browser scenarios, rerun successfully within the current 15-scenario suite, cover sample conversion and real downloads, edited dimensions and stale exports, exact mm/in conversion, saved-project recovery, own-photo calibration, malformed upload recovery, keyboard dialog focus and Escape, mobile overflow, missing export recovery, and temporary-export cleanup. The sample scenario checks browser console errors and page exceptions; none occurred. The rendered workbench had zero violations in the selected axe-core WCAG A/AA checks. This is not a claim of complete accessibility conformance or a substitute for assistive-technology user testing.

The environment's `sites-preview` relay was unavailable. Browser verification used actual Chromium against the running app and development proxy, with screenshots and interaction tests; no hosted preview or deployment is claimed.

## Design, print and local-assistant follow-up

The complete run for the design, print, and assistant changes passed 142 Python tests, production typecheck/build, and 15 browser scenarios. Additional scenarios cover reviewed multi-setting suggestions, explicit rejection, Undo after building, stale responses, saved recipes, printer search, actual parts ZIP geometry, and mobile accessibility. The viewer keeps a stable canvas across model changes; both a multipart-build regression and genuine context-loss recovery were tested and corrected before this passing run.

Actual rendered evidence, without AI-response fixtures:

- [Design and print controls](docs/images/design-print.png), 1464 × 1241, and [mobile controls](docs/images/design-print-mobile.png), 366 × 1997, at a 390 px viewport.
- [Separated actual pieces](docs/images/separated-pieces.png), 723 × 572. The original 80 mm / 4 mm source measurements remain intact; 150% XY and 125% thickness produce a 120 × 51.02 × 5 mm assembly. Two real pieces are shown with display-only separation and Ocean/PETG appearance.
- [Printer profile facts](docs/images/printer-profile.png) show the selected Prusa MK4S nozzle profile, declared limits, unknown hardware details, and source attribution.
- [Local assistant](docs/images/local-assistant.png) and [mobile assistant](docs/images/local-assistant-mobile.png) show the actual running Ollama server's empty model list. They do not present fabricated model answers or imply inference was tested.

The capture run recorded no page exceptions and no horizontal overflow. The design panel uses two desktop columns and a single mobile column, with optional profile facts collapsed by default. Material appearance is illustrative; the separated view is for inspection and does not define a slicer plate arrangement. Main color, measurements, control labels, and print-fit limitations remain visible and consistent.

**Open Questions / accepted differences**

- The reference depicts a demonstration height of 30 mm; the real traced sample produces 34.05 mm at an 80 mm width. The interface reports the calculated geometry instead of copying a mock measurement.
- The photo-derived outline is polygonal. The app does not add decorative bevels or analytic circles that are absent from the generated solid.
- Named, keyboard-accessible view buttons replace the illustrative orientation cube. Outline dots show sampled geometry; direct vertex editing is outside this release.
- Helpful sample labeling, explicit units, and capture guidance add modest content beyond the static concept.

**Implementation Checklist**

- [x] Resolve and inspect the selected visual target.
- [x] Use real source imagery, traced geometry, and a functioning CAD viewer.
- [x] Compare the same desktop state and density.
- [x] Fix all identified P0/P1/P2 issues and recapture.
- [x] Verify core interactions, console errors, keyboard behavior, and mobile layout.
- [x] Preserve useful limitations in product copy and documentation.

**Follow-up Polish**

P3: analytic curve fitting and a more elaborate orientation cube could improve the engineering experience in a future release. They are not represented as implemented features.

final result: passed
