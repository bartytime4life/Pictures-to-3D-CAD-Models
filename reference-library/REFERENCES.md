# Annotated source directory

86 resources. Checked November 8, 2026. Review depth is recorded for each entry; links are not claims of full-document review.

## Capture & reconstruction

### [COLMAP reconstruction tutorial](https://colmap.github.io/tutorial)

Official documentation | Beginner–advanced | Search-index content checked

Explains sparse structure from motion and dense reconstruction from overlapping photographs.

**Limit:** Use for multi-view recovery; metric scale and independent dimensions still need external references.

### [Meshroom capture guide](https://meshroom-manual.readthedocs.io/en/latest/capturing/capturing.html)

Official documentation | Beginner | Search-index content checked

Practical photography guidance: coverage, diffuse lighting, stable focal length, and turntable backgrounds.

**Limit:** Versioned manual; image overlap is guidance, not a dimensional-accuracy guarantee.

### [COLMAP installation and build options](https://colmap.github.io/install.html)

Official documentation | Intermediate | Page content checked

Check supported builds, compute backends, and dependencies before choosing a reconstruction setup.

**Limit:** Read the instructions for the chosen release; no local installation was performed.

### [Smithsonian photogrammetry and 3D technologies](https://mci.si.edu/3d-technologies)

Institutional guidance | Beginner | Search-index content checked

Introduces image-based digitization in conservation.

**Limit:** Conservation workflows may prioritize visual recording over engineering fit.

### [colmap/colmap](https://github.com/colmap/colmap)

GitHub repository | Intermediate–advanced | Repository metadata checked

Sparse and dense reconstruction from photographs.

**Limit:** Inspect the installed build for supported compute backends.

### [alicevision/Meshroom](https://github.com/alicevision/Meshroom)

GitHub repository | Intermediate–advanced | Repository metadata checked

Graph-based reconstruction workflows in the AliceVision ecosystem.

**Limit:** Pipeline and GPU requirements vary by release; inspect current setup instructions.

### [cdcseacave/openMVS](https://github.com/cdcseacave/openMVS)

GitHub repository | Intermediate–advanced | Repository metadata checked

Dense reconstruction and meshing tools.

**Limit:** Inspect the chosen pipeline's required camera/scene inputs.

## Geometry & measurement

### [OpenCV camera calibration](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)

Official documentation | Intermediate | Page content checked

Camera intrinsics, lens distortion, and undistortion using calibration targets.

**Limit:** Calibration residuals do not by themselves establish object-space accuracy.

### [OpenCV homography tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html)

Official documentation | Intermediate | Page content checked

Projective mapping and perspective correction for a plane.

**Limit:** A single plane correction cannot recover arbitrary 3D depth.

### [fSpy camera matching](https://fspy.io/)

Official project | Beginner–intermediate | Page content checked

Recover a useful camera match for interpreting perspective in one still image.

**Limit:** Camera matching does not reveal hidden shape or establish all dimensions.

### [CloudCompare distance computation](https://www.cloudcompare.org/doc/wiki/index.php/Distances_Computation)

Official documentation | Intermediate | Page content checked

Explains cloud-to-cloud and cloud-to-mesh comparison.

**Limit:** Nearest-neighbor distance depends on sampling; alignment and reference quality matter.

### [Open3D ICP registration tutorial](https://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html)

Official documentation | Intermediate | Page content checked

Refine alignment from an initial approximate transform.

**Limit:** A plausible local alignment can still be incorrect, especially for repeated or symmetric shapes.

### [CloudCompare/CloudCompare](https://github.com/CloudCompare/CloudCompare)

GitHub repository | Intermediate–advanced | Repository metadata checked

Point-cloud registration and deviation inspection.

**Limit:** Compare against an independent, appropriately aligned reference.

### [isl-org/Open3D](https://github.com/isl-org/Open3D)

GitHub repository | Intermediate–advanced | Repository metadata checked

Programmable processing of point clouds and meshes.

**Limit:** Library outputs need coordinate, unit, and quality checks.

### [JCGM 100:2008 Guide to the expression of uncertainty in measurement (GUM)](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf)

International guidance document | Advanced | Page content checked

Defines standard uncertainty and Type B evaluation, including the bounded rectangular case where a quantity known only within ±a has standard uncertainty a/√3.

**Limit:** A rounding interval or published bound is one input. The guide does not supply perspective, distortion, picking, or manufacturing errors for an image-based measurement.

## CAD & drawings

### [FreeCAD: importing and scaling reference images](https://freecad.github.io/Website/pl/news/tutorial-importing-and-using-scaled-reference-images/)

Official tutorial | Beginner | Page content checked

Import a reference image and calibrate it using a known distance.

**Limit:** Use coplanar measurement references; retain measured dimensions separately.

### [FreeCAD TechDraw workbench](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/TechDraw_Workbench.md)

Official documentation | Beginner–intermediate | Repository document read

Create drawing views, dimensions, sections, annotations, and PDF/SVG/DXF exports from 3D models.

**Limit:** A drawing conveys design intent only when datums, dimensions, and inspection requirements are chosen.

### [FreeCAD traditional 2D drafting manual](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Manual_Traditional_2D_drafting.md)

Official documentation | Beginner | Search-index content checked

Introduces Draft as a bridge between 2D geometry and 3D modeling.

**Limit:** Use Sketcher for constrained profiles and TechDraw for model-derived drawings.

### [Fusion canvas calibration concepts](https://autodeskfusion360.github.io/FusionAPIReference/Fusion_API_Documentation/files/Canvases_UM.htm)

Official documentation | Beginner–intermediate | Search-index content checked

Explains canvas size and calibration in Fusion.

**Limit:** License and platform requirements must be checked separately.

### [Fusion: convert a mesh to a solid](https://help.autodesk.com/cloudhelp/ENU/Fusion-Mesh/files/MESH-CONVERT-TO-SOLID.htm)

Official documentation | Intermediate | Page content checked

Describes faceted and prismatic mesh conversions and their timeline options.

**Limit:** Conversion is not proof of recovered original feature history; availability can depend on entitlement.

### [Autodesk University: reverse engineering with imported data](https://static.au-uw2-prd.autodesk.com/Class_Handout_CP323607_Reverse_Engineering_with_Imported_Data_in_Fusion_360_Jeff_Strater.pdf)

Official training PDF | Intermediate | Search-index content checked

Long-form training on mesh, canvas, and imported-data workflows.

**Limit:** Older course; use current documentation for interface and licensing details.

### [McNeel reverse engineering guide](https://wiki.mcneel.com/rhino/reverseengineering)

Official documentation | Intermediate–advanced | Search-index content checked

Orientation to reconstructing editable surfaces from mesh or point-cloud measurements.

**Limit:** Some linked examples are historical; distinguish surface reconstruction from mesh wrapping.

### [CadQuery documentation](https://cadquery.readthedocs.io/en/latest/)

Official documentation | Intermediate | Page content checked

Python-based parametric CAD with engineering export formats.

**Limit:** A modeling tool, not an automatic photograph measurement system.

### [build123d documentation](https://build123d.readthedocs.io/en/latest/)

Official documentation | Intermediate | Page content checked

Python parametric B-rep modeling based on Open Cascade.

**Limit:** Pin a release when reproducing examples; latest documentation can describe development code.

### [OpenSCAD documentation](https://openscad.org/documentation)

Official documentation | Beginner–intermediate | Search-index content checked

Scripted constructive geometry, extrusion, and reusable dimensions.

**Limit:** Keep the script as editable source; mesh export is not a feature-history CAD exchange.

### [Inkscape: tracing an image](https://inkscape-manuals.readthedocs.io/en/1.1/tracing-an-image.html)

Project documentation | Beginner | Search-index content checked

Turn bitmap silhouettes into vector paths for cleaned-up profiles and extrusion.

**Limit:** Trace results need scale, node simplification, and closed-loop checks.

### [FreeCAD/FreeCAD](https://github.com/FreeCAD/FreeCAD)

GitHub repository | Intermediate–advanced | Repository metadata checked

Editable mechanical CAD and model-derived drawings.

**Limit:** Build constraints from measured features; importing a mesh alone does not restore intent.

### [gumyr/build123d](https://github.com/gumyr/build123d)

GitHub repository | Intermediate–advanced | Repository metadata checked

Python-based CAD construction.

**Limit:** Pin dependencies for repeatable model generation.

### [openscad/openscad](https://github.com/openscad/openscad)

GitHub repository | Intermediate–advanced | Repository metadata checked

Scripted constructive-solid models.

**Limit:** Use native source for editability; do not equate STL with feature history.

### [CadQuery/cadquery](https://github.com/CadQuery/cadquery)

GitHub repository | Intermediate–advanced | Repository metadata checked

Parametric CAD as Python code.

**Limit:** Photo interpretation and measurement remain upstream tasks.

## Mesh processing

### [Rhino ShrinkWrap](https://www.rhino3d.com/features/shrinkwrap/)

Official feature guide | Intermediate | Search-index content checked

Constructs a watertight mesh around several geometry types.

**Limit:** Wrapping can alter gaps, cavities, and small features; inspect deviations afterward.

### [MeshLab project and capabilities](https://www.meshlab.net/)

Official project | Beginner–intermediate | Page content checked

Mesh cleaning, inspection, healing, simplification, and conversion.

**Limit:** Smoothing and decimation can remove dimensional features.

### [Open3D surface reconstruction](https://www.open3d.org/docs/release/tutorial/geometry/surface_reconstruction.html)

Official documentation | Intermediate | Page content checked

Alpha shapes, ball pivoting, and Poisson reconstruction from point clouds.

**Limit:** Normals, sampling, and low-support regions influence the resulting mesh.

### [cnr-isti-vclab/meshlab](https://github.com/cnr-isti-vclab/meshlab)

GitHub repository | Intermediate–advanced | Repository metadata checked

Interactive processing of scanned triangle meshes.

**Limit:** Retain a raw copy before smoothing, repair, or decimation.

### [mikedh/trimesh](https://github.com/mikedh/trimesh)

GitHub repository | Intermediate–advanced | Repository metadata checked

Mesh loading, analysis, transformations, and export.

**Limit:** Watertightness is only one acceptance criterion.

## Advanced geometry

### [CGAL shape detection](https://doc.cgal.org/latest/Shape_detection/index.html)

Official documentation | Advanced | Search-index content checked

Primitive detection and region growing for point sets and meshes.

**Limit:** Detected primitives are hypotheses that need tolerance and coverage checks.

### [CGAL polygon mesh processing](https://doc.cgal.org/latest/Polygon_mesh_processing/)

Official documentation | Advanced | Search-index content checked

Mesh geometry, repair, remeshing, intersections, and distance tools.

**Limit:** Check the license of the particular CGAL packages used.

### [MIT Shape Interrogation hyperbook](https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/mathe.html)

University textbook | Advanced | Page content checked

Mathematical reference for curves, surfaces, NURBS, intersections, curvature, and offsets.

**Limit:** Study selectively after learning vectors, calculus, and parametric curves.

### [Keenan Crane: Discrete Differential Geometry](https://www.cs.cmu.edu/~kmcrane/Projects/DDG/)

University course | Advanced | Page content checked

Develops computational surface geometry and geometric operators.

**Limit:** Foundational material; not an end-to-end CAD conversion recipe.

### [Hartley and Zisserman: Multiple View Geometry](https://www.robots.ox.ac.uk/~vgg/hzbook/)

Author book resources | Advanced | Page content checked

Sample chapters and supporting material for projective and multi-view geometry.

**Limit:** The landing page provides selected resources, not necessarily the full book.

### [libigl tutorial](https://libigl.github.io/tutorial/)

Official documentation | Advanced | Search-index content checked

Hands-on geometry processing and differential operators.

**Limit:** Programmer-oriented; component licenses should be read before redistribution.

### [Geometry Central](https://geometry-central.net/)

Official documentation | Advanced | Page content checked

Surface mesh data structures and geometry-processing algorithms.

**Limit:** Useful for custom tools; not a desktop reverse-engineering workflow by itself.

### [libigl/libigl](https://github.com/libigl/libigl)

GitHub repository | Intermediate–advanced | Repository metadata checked

Geometry-processing algorithms and experiments.

**Limit:** API license metadata differs from project description; inspect component licenses.

### [CGAL/cgal](https://github.com/CGAL/cgal)

GitHub repository | Intermediate–advanced | Repository metadata checked

Computational geometry primitives and mesh algorithms.

**Limit:** Licensing varies among packages; review selected modules.

### [sxyu/sdf](https://github.com/sxyu/sdf)

GitHub repository | Intermediate–advanced | Repository metadata checked

Convert a triangle mesh into a continuous signed distance representation.

**Limit:** This direction is mesh to distance field, not photograph to CAD.

### [KHK: calculation of gear dimensions](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html)

Manufacturer technical reference | Intermediate–advanced | Page content checked via HTTP

Dimension relationships for spur, internal, helical, and other gear systems.

**Limit:** Use the correct gear family and profile-shift assumptions; the equations do not establish print strength or backlash.

## Printing & validation

### [Prusa: modeling with 3D printing in mind](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135)

Manufacturer guide | Beginner | Page content checked

Design constraints for walls, overhangs, orientation, and fitting parts.

**Limit:** No universal clearance; validate the printer, material, and orientation actually used.

### [Prusa: layers and perimeters](https://help.prusa3d.com/article/layers-and-perimeters_1748)

Manufacturer guide | Beginner–intermediate | Search-index content checked

Connects shell and layer settings with printable geometry.

**Limit:** Slicer settings and extrusion width affect thin-wall outcomes.

### [Blender 3D Print Toolbox extension](https://extensions.blender.org/add-ons/print3d-toolbox/)

Official extension listing | Beginner–intermediate | Search-index content checked

Tools for mesh checks, volume, wall work, orientation, and print preparation.

**Limit:** An automated mesh check cannot validate mechanical fit or load capacity.

### [3MF specification directory](https://3mf.io/spec/)

Format specification | Intermediate | Page content checked

Authoritative entry point to 3MF core and extension specifications.

**Limit:** Check which extensions the exporter and slicer actually support.

### [3MF Core Specification source](https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md)

Format specification | Advanced | Search-index content checked

Detailed model, mesh, coordinate, and packaging requirements.

**Limit:** A 3MF project from a slicer may also contain vendor-specific settings.

### [NIST additive manufacturing test artifact](https://www.nist.gov/publications/additive-manufacturing-test-artifact)

Primary research | Intermediate | Page content checked

Feature-based evaluation of additive manufacturing geometry.

**Limit:** The test concept transfers; published system results are not predictions for a hobby printer.

### [prusa3d/PrusaSlicer](https://github.com/prusa3d/PrusaSlicer)

GitHub repository | Intermediate–advanced | Repository metadata checked

Slicing and toolpath preview.

**Limit:** Recheck the selected printer profile and resulting dimensions.

### [OrcaSlicer/OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer)

GitHub repository | Intermediate–advanced | Repository metadata checked

Slicing and calibration workflows.

**Limit:** A successful slice does not establish physical fit or strength.

### [PrusaSlicer cut tool with connectors](https://help.prusa3d.com/article/cut-tool_1779)

Manufacturer guide | Beginner–intermediate | Page content checked

Cuts a model into parts and generates plug, dowel, or snap connectors for reassembly.

**Limit:** The article is filed under a legacy slicer release; check the current version, and test connector fit with a coupon in the intended material.

### [Formlabs: hollowing models and adding drain holes](https://formlabs.com/blog/how-to-hollow-out-3d-models/)

Manufacturer guide | Beginner–intermediate | Page content checked

Walks through orienting, hollowing, and adding drain holes so resin can escape and cupping is avoided, including adding at least one extra drain hole.

**Limit:** Vendor workflow for its own software and printers; wall thickness, hole size, and orientation must be validated for the actual resin and machine.

## Biology & datasets

### [NIH 3D](https://3d.nih.gov/)

Institutional model database | Beginner | Page content checked

Discover biomedical and scientific 3D models and workflows.

**Limit:** Read each entry's provenance, units, version, and permitted uses.

### [NIH 3D FAQs](https://3d.nih.gov/faqs)

Institutional guidance | Beginner | Search-index content checked

Model use, citation, and platform guidance.

**Limit:** A repository entry is not automatic clinical or manufacturing approval.

### [MorphoSource repository description](https://github.com/MorphoSource/MorphoSource)

Official repository | Beginner–intermediate | Search-index content checked

Biological, fossil, and cultural-object 3D, 2D, and audiovisual data platform.

**Limit:** The live catalog blocked automated access; individual datasets and permissions were not inspected.

### [Smithsonian 3D digitization program](https://dpo.si.edu/3d-digitization-program)

Institutional program | Beginner | Search-index content checked

Object capture, research, access, and collection digitization.

**Limit:** Verify the license and available download on each collection record.

### [3D Slicer image segmentation](https://slicer.readthedocs.io/en/latest/user_guide/image_segmentation.html)

Official documentation | Intermediate | Search-index content checked

Delineate structures in image volumes before surface extraction.

**Limit:** CT/MRI slice stacks are a different input problem from exterior photographs.

### [3D Slicer segmentations and export](https://slicer.readthedocs.io/en/latest/user_guide/modules/segmentations.html)

Official documentation | Intermediate | Search-index content checked

Segmentation representations and creating surfaces for printing.

**Limit:** Voxel spacing, threshold choices, and smoothing affect final geometry.

### [3D Slicer training compendium](https://training.slicer.org/)

Official tutorials | Beginner–intermediate | Search-index content checked

Guided exercises with sample data.

**Limit:** Use sample datasets for learning; do not infer clinical fitness from an export.

### [Stanford 3D scanning repository](https://graphics.stanford.edu/data/3Dscanrep/)

University dataset | Intermediate | Page content checked

Classic range-scan and mesh data for registration and reconstruction practice.

**Limit:** These are scanner datasets, not evidence of phone-photogrammetry accuracy.

## Research literature

### [Structure-from-Motion Revisited](https://openaccess.thecvf.com/content_cvpr_2016/html/Schonberger_Structure-From-Motion_Revisited_CVPR_2016_paper.html)

Primary research | Advanced | Search-index content checked

Schönberger and Frahm, CVPR 2016: foundation for the COLMAP reconstruction pipeline.

**Limit:** Search-index abstract checked; direct page fetch returned 403.

### [DeepCAD author project page](https://www.cs.columbia.edu/cg/deepcad/)

Primary research | Advanced | Page content checked

Wu, Xiao, and Zheng, ICCV 2021: generative modeling of CAD operation sequences.

**Limit:** Research on CAD representation and generation is not a dimensional photo-conversion guarantee.

### [BrepGen paper](https://damassets.autodesk.net/content/dam/autodesk/www/pdfs/brepgen.pdf)

Primary research PDF | Advanced | Search-index content checked

Xu and collaborators, SIGGRAPH 2024: B-rep generation with structured latent geometry.

**Limit:** Generation of valid geometry and recovery of the exact observed part are different tasks.

### [Photogrammetry-derived printed sheep scapula comparison](https://pubmed.ncbi.nlm.nih.gov/35014052/)

PubMed primary study | Intermediate | Page content checked

An anatomy example comparing models made with PLA and TPU.

**Limit:** Single study and application; no general phone accuracy or material equivalence is inferred.

### [Optical face scanner for customized 3D-printed spectacles](https://pubmed.ncbi.nlm.nih.gov/35629524/)

PubMed bibliographic record | Intermediate | Bibliographic metadata only

A related application linking anatomical surface capture with customized printed products.

**Limit:** Title and identifiers checked through Entrez; abstract and full methods were not reviewed.

### [rundiwu/DeepCAD](https://github.com/rundiwu/DeepCAD)

GitHub repository | Intermediate–advanced | Repository metadata checked

Implementation accompanying the DeepCAD research paper.

**Limit:** Research code; repository metadata reports its last push in 2024.

### [samxuxiang/BrepGen](https://github.com/samxuxiang/BrepGen)

GitHub repository | Intermediate–advanced | Repository metadata checked

Official implementation for BrepGen.

**Limit:** Research generation method, not an assured photo-measurement product.

### [Analysis of the Accuracy of CAD Modeling in Engineering and Medical Industries Based on Measurement Data Using Reverse Engineering Methods](https://scispace.com/papers/analysis-of-the-accuracy-of-cad-modeling-in-engineering-and-36nxm62vq6)

SciSpace scholarly record | Intermediate–advanced | Abstract / scholarly record

Turek and colleagues (2024). Tracks reconstruction and CAD-modeling deviations across several shapes.

**Limit:** Abstract and complete bibliographic record reviewed; reported deviations are setup-specific.

### [Towards the Fitting of Parametric 2D Sketches and 3D CAD Models to Point Clouds of Digitized Assemblies for Reverse Engineering](https://scispace.com/papers/towards-the-fitting-of-parametric-2d-sketches-and-3d-cad-1djsfr3w67)

SciSpace scholarly record | Intermediate–advanced | Abstract / scholarly record

Parametric sketch and CAD fitting to scanned assemblies (2019).

**Limit:** Abstract-level discovery; inspect the paper before implementing its fitting method.

### [Investigation of the accuracy of close-range photogrammetry – a 3d printing case study](https://scispace.com/papers/investigation-of-the-accuracy-of-close-range-photogrammetry-2hhol7wrqs)

SciSpace scholarly record | Intermediate–advanced | Abstract / scholarly record

Small-object photogrammetry and 3D-printing accuracy case study (2015).

**Limit:** One case study; accuracy and repeatability are separate questions.

### [Reverse Engineering Using Close Range Photogrammetry for Additive Manufactured Reproduction of Egyptian Artifacts and Other Objets d'art](https://scispace.com/papers/reverse-engineering-using-close-range-photogrammetry-for-3m0wn3gwp8)

SciSpace scholarly record | Intermediate–advanced | Abstract / scholarly record

Photogrammetry-to-additive-manufacturing workflow for cultural artifacts (2015).

**Limit:** Useful workflow precedent; does not establish mechanical mating tolerances.

### [Experimental comparison of photogrammetry for additive manufactured parts with and without laser speckle projection](https://scispace.com/papers/experimental-comparison-of-photogrammetry-for-additive-4unoc5f5vu)

SciSpace scholarly record | Intermediate–advanced | Abstract / scholarly record

Study of surface appearance and projected speckle for scanning printed parts (2017).

**Limit:** Abstract reviewed; no instrumentation or accuracy claim is generalized.

### [CADFit: Precise Mesh-to-CAD Program Generation with Hybrid Optimization](https://scispace.com/papers/cadfit-precise-mesh-to-cad-program-generation-with-hybrid-fl4odx8809fi)

SciSpace scholarly record | Intermediate–advanced | Discovery abstract only

Research on recovering editable CAD operations from meshes (2026).

**Limit:** Discovery lead only: publication status, code, and benchmark details need full-paper verification.

### [Image2CADSeq: Computer-Aided Design Sequence and Knowledge Inference from Product Images](https://scispace.com/papers/image2cadseq-computer-aided-design-sequence-and-knowledge-71qfjvt88v04)

SciSpace scholarly record | Intermediate–advanced | Discovery abstract only

Research on recovering CAD sequences from product images (2026).

**Limit:** Discovery lead only; no local implementation or real-part accuracy test performed.

### [RealCAD: Towards Real-World Image-to-CAD Reconstruction under Domain Shift and Parameter Bias](https://scispace.com/papers/realcad-towards-real-world-image-to-cad-reconstruction-under-o7g04f6k963j)

SciSpace scholarly record | Intermediate–advanced | Discovery abstract only

Research on synthetic-to-real domain shift and CAD parameter bias (2026).

**Limit:** Discovery lead only; do not treat a search abstract as independent validation.

## AI reconstruction

### [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS)

GitHub repository | Intermediate–advanced | Repository metadata checked

Image-conditioned 3D asset generation research.

**Limit:** Generated unseen surfaces are hypotheses; inspect weights and dependency terms separately.

### [nerfstudio-project/nerfstudio](https://github.com/nerfstudio-project/nerfstudio)

GitHub repository | Intermediate–advanced | Repository metadata checked

Neural rendering research and reconstruction tooling.

**Limit:** View-synthesis quality and recovered surface accuracy must be tested separately.

### [Tencent-Hunyuan/Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)

GitHub repository | Intermediate–advanced | Repository metadata checked

Image-to-3D shape and texture generation research.

**Limit:** Inspect model-specific terms and hardware requirements before use.

## Formats, posing & assets

### [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)

Format specification | Intermediate | Page content checked

Defines the glTF coordinate system and units: right-handed, +Y up, +Z forward, and linear distances in metres.

**Limit:** Many CAD and slicing tools present Z-up millimetres; convert explicitly on import and check extents rather than trusting a viewer.

### [Blender manual: posing armatures](https://docs.blender.org/manual/en/latest/animation/armatures/posing/introduction.html)

Official documentation | Intermediate | Page content checked

Explains Pose Mode: transforming bones deforms the skinned mesh relative to the armature rest position, which is how a static character mesh is re-posed.

**Limit:** Re-posing a dense sculpt needs skin weights and joint cleanup; a convincing on-screen pose still needs wall, support, and contact checks.

### [Blender manual: sculpting](https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/index.html)

Official documentation | Beginner–intermediate | Page content checked

Brush-based Sculpt Mode for shaping over a blockout and repairing deformation after posing.

**Limit:** Sculpted surfaces are design interpretation; measured interfaces should remain parametric and be joined afterward.

### [Creative Commons license types](https://creativecommons.org/share-your-work/cclicenses/)

Institutional guidance | Beginner | Page content checked

Summarizes common license elements (attribution, non-commercial, no derivatives, share-alike) that govern many shared models and images.

**Limit:** Marketplace and custom licenses differ from Creative Commons; read the terms attached to each asset. Character and trademark rights can apply regardless of the file license.

