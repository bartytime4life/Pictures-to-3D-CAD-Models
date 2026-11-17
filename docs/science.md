# Science and measurement

The studio makes the sources of information explicit: image pixels describe visible shape, a known length establishes scale, and entered thickness establishes extrusion depth. Interactive scenarios help explain these relationships; they are not a calibration certificate or a substitute for independent physical measurements.

## Pixel scale and reference sensitivity

For a known length `L` millimeters spanning `p` image pixels, the nominal scale is `s = L / p` millimeters per pixel. A feature spanning `q` pixels has nominal length `q × s`. Uniform design scale then changes the requested output without changing the original measurement.

A reference length is useful only when its endpoints identify the intended feature and the relevant surfaces have an appropriate geometric relationship. A ruler elsewhere in the scene, a tilted reference, a rounded visible edge or an incorrectly identified common object can produce a systematic error.

The Science lab and reference tools explore how endpoint placement changes the calculated size under stated assumptions. Such shifts are sensitivity scenarios. They omit other potentially significant inputs, including known-length measurement error, perspective, lens distortion, blur, segmentation and model mismatch. A complete uncertainty analysis must identify significant inputs and their relationships; NIST describes propagation through sensitivity coefficients and covariance. [NIST Technical Note 1297, Appendix A](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-law-propagation-uncertainty).

In the Science lab, a shift of `e` pixels **per reference endpoint** gives trial reference spans `p + 2e` and `p - 2e`. The displayed output lengths are `qL / (p + 2e)` and `qL / (p - 2e)`; the reference span must exceed `2e`. The outline span and known length stay fixed in this scenario. This interval is not a statistical confidence interval.

Read [reference sensitivity](reference-sensitivity.md) for the workbench's actual endpoint contract and [engineering verification](engineering-model.md) for an independent source-height decision. A nominal coin/card/reference preset should be checked against the physical object rather than treated as a measured value.

## Perspective and reference sheets

An ordinary front-on trace uses a planar outline and uniform scale. A suitable known rectangular sheet enables the separate sheet pipeline to estimate perspective and a limited lens correction. That correction depends on visible sheet geometry and the method's assumptions; it does not recover arbitrary depth.

The pinhole model maps 3D points through camera intrinsics, orientation and translation before perspective division; distortion requires additional parameters. This explains why image scale can vary with orientation and distance. [OpenCV camera-calibration documentation](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html).

The [reference-sheet guide](reference-sheet.md) documents the implementation's supported captures, fitted edges and failure notices. Important holes and radii require independent checks, especially when source support is weak or a fitted boundary falls back to a polygon.

## Layers and print resolution

The Science lab models one first layer of height `f`, followed by constant layers of height `h`. For target height `H`, it uses `N = 1 + ceil(max(0, H - f) / h)` and displays the ideal stack `f + (N - 1)h`. For example, a 4 mm part with a 0.2 mm first layer and 0.2 mm regular layers gives 20 layers. If the first layer already exceeds the target, the scenario still shows one layer and the excess height. Real slicers can use variable layers, surface-dependent behavior and different rounding or machine-specific limits.

The application's process plan accepts layer height from 0.05 to 1.2 mm and no greater than the selected nozzle diameter. These are input bounds, not a recommendation that every allowed combination will print well. Prusa's guidance recommends keeping layer height below approximately 80% of nozzle diameter and discusses the independent first-layer setting. Its perimeter guidance also explains overlap, so wall thickness should not be inferred simply as wall count multiplied by nominal line width. [Prusa: layers and perimeters](https://help.prusa3d.com/article/layers-and-perimeters_1748).

The process presets are starting points for review. Increasing walls or infill does not establish a quantified strength, print duration or material consumption. Native slicing and material-specific testing remain separate.

## Bed containment and orientation

For each flat built piece, the backend checks thickness against build height and searches supported rectangular XY placements with the selected margin. Polygon cases use their footprint. Fitted curves can use an outer enclosure: a successful enclosure fit is conservative, while a failed outer bound may remain unknown.

The preparation display projects the actual mesh at an inspection angle and centers its bounds on the displayed bed. Its footprint is a visual mesh envelope, not a new exact solver result. Changing the view angle, grid or margin visibility changes no geometry, bed margin or saved process setting. The saved fit result remains visible separately. Neither result models support volume, raft/brim width, excluded bed zones, multiple-object collisions or toolpaths. See [placement mathematics](research.md#continuous-angle-rectangular-placement) and [print planning](print-planning.md).

## Measured fit and clearance

A clearance requirement compares physical mating dimensions under a declared sign convention. A useful scenario separates the intended nominal dimensions, a measured printed result and a proposed adjustment. A single test coupon describes that printer/material/settings combination; it is not a universal correction for every part, axis or feature size.

The Science lab's fit scenario uses a measured hole bias: `bias = measured hole − coupon CAD hole`. It sets the desired physical hole to `measured shaft + desired diametral clearance`, then suggests `next CAD hole = desired physical hole − bias`. Radial clearance is half the diametral value; negative clearance denotes interference. For example, a 10 mm CAD hole measured at 9.8 mm gives a −0.2 mm bias. A 10 mm shaft with 0.2 mm desired diametral clearance produces a trial CAD diameter of 10.4 mm.

This arithmetic assumes the same additive bias transfers to the next hole. It does not change the CAD recipe or establish that thermal shrinkage, hole compensation and mechanical loading follow that model. Print and measure a relevant coupon, reserve independent checks and record the result. See the [fit-coupon examples](../reference-library/OPENSCAD.md) and [print-acceptance template](../reference-library/templates/PRINT-ACCEPTANCE.md).

## Relief and lithophane interpretation

A brightness relief maps image intensity into height; that does not make bright pixels measured high points. A lithophane uses an optical attenuation model to choose thickness, with calibration needed for actual filament and lighting. AI depth predicts relative surface structure under a learned model and does not infer trusted physical dimensions. Supported elevation data has a separate unit/scale workflow. See the [relief science and calibration guide](relief.md#the-science).

## Scenario files and reproducibility

Use the Science workspace's export/import controls to preserve all three experiments in `pictures-to-cad-science.json`. Valid scenarios autosave locally; invalid drafts preserve the last valid saved values. Knowledge notes and pins have a separate `pictures-to-cad-notebook.json` export. These files are independent of a CAD project or slicer package. Record the source measurements, units, interpretation and expected outcome alongside exported values, and rerun the scenario after edits.

Browser storage belongs to an origin and browser profile and can be cleared. Export important notes and scenarios to retain portable copies. Do not treat saved local state as a backed-up engineering record.

## Research and evidence

The repository includes numerical operators and historical synthetic studies beyond the product workflow. Some developer APIs exist only in recorded branches. Their reports retain fixed inputs, source bindings, negative outcomes and known non-identifiability results. Start with [research methods](research.md), [research and validation index](research-index.md), [source scope](project-status.md) and [validation overview](validation.md).

Keep the questions separate: did the code run, did the browser render, did the receiving CAD/slicer import the file, did the toolpath make sense, and did the physical part meet its requirement? Each needs its own evidence.
