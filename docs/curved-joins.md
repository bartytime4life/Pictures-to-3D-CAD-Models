# Circle-consistent joins and retained outlines

[Documentation index](README.md) · [Critical arc checks](exports.md#verify-critical-arc-geometry) · [Blur frames](blur-frames.md)

A fitted circle has a centre and radius. Joining it to neighboring geometry
must not silently replace it with another circle. The canonical-join port
addresses that digital representation problem in reference-sheet tracing. It
does not establish the physical radius of a photographed part, select a new
Gaussian correction model or add workbench controls.

The [current source-bound record](validation/directional-free-arcs.md) separates
this main-based port from its historical implementation and from conditional
optical-model experiments. Existing trace/build controls and saved profile
formats remain unchanged.

## Why a closed, valid solid was insufficient

The previous final assembly could use perpendicular feet on neighboring lines
as an arc's endpoints while retaining a midpoint from the fitted circle. Those
three points can define a different centre and radius. A downstream CAD kernel
can correctly extrude that different circle into a valid solid, so validity
alone does not detect the discrepancy.

There was also a reachability problem: an exact circular segment closed by a
chord needs two distinct line/circle intersections. Using the same foot twice
could reject a suitable analytic fit before its final representation was built.
Preserving a major arc requires its signed sweep and interior witness; choosing
the shorter sector from endpoints alone changes the boundary.

## One stored circle, explicit intersections

For an accepted final arc, the join construction retains the stored centre
`C` and radius `R`. A neighboring line intersects that circle at its actual
roots, rather than supplying an unrelated perpendicular foot. The emitted
start, interior and end points must describe the same circle in the selected
sector. A final check compares their reconstructed circle with `C,R` in local
coordinates.

Reconstructing a three-point circle also uses local coordinate differences,
avoiding subtraction of large squared world coordinates. When a fillet or slot
cap changes centre or radius, its interior witness moves with the circle and
keeps its original angular direction. That witness selects an arc sector; it
is not a newly observed edge point or a physical radius measurement.

Where a line has two roots, the choice is constrained by ordered source-end
witnesses, line traversal and the arc's signed sweep. The construction compares
complete cyclic join choices under a minimum-edit objective; choosing the
nearest root at every junction independently can reverse a line or select the
wrong sector. A separated winner under this objective is a geometric fitting
decision, not a likelihood, a confidence level or proof of the physical edge.

The search and arithmetic have finite work limits. Missing source provenance,
no intersection, ambiguous alternatives, unstable near contact, unsupported
arithmetic or an unresolved ordered cycle can make an analytic construction
unavailable. Prescribed tangent geometry and a free near-contact arc have
different rules: the port does not impose tangency on a free arc merely to make
an export close.

These are engineering floating-point checks, not certified exact arithmetic or
an endpoint uncertainty bound. Local circle consistency and cyclic ordering do
not prove that the whole ring is simple; final polygon/profile validation still
applies.

## Initial fitting and final export are different decisions

Initial geometric eligibility can try the canonical construction first. If it
is unavailable, an earlier line-foot/midpoint proxy can still let a supported
blur-shrunken candidate reach the existing correction and fitting stage. That
proxy is an eligibility construction. It does not become the final analytic
export or establish unobserved join provenance.

Final assembly must construct each accepted analytic ring separately, after
radius correction and design-intent changes. This repair does not replace the
scalar free-circle/free-arc series with an exact finite Gaussian disk fit.
Direction-dependent partial-arc bias, finite neighboring boundaries, wall/tone
effects and the mixed-frame approximations described in [blur frames](blur-frames.md)
remain separate model limitations. A perfectly represented fitted circle can
still be the wrong physical circle.

## When a join cannot be constructed

An unavailable final analytic join normally retains only the affected source
boundary as a traced outline and adds a targeted reference note and workbench
warning. Other accepted rings and the sheet calibration remain available. A
retained boundary is line geometry; it must not acquire a rejected arc's radius
or a claim that the radius was measured.

Notices identify the outer boundary or affected hole and the unavailable join.
Saved notes can summarize large groups of recovered boundaries, while workbench
warnings retain the individual causes.

Radius diagnostics, design-intent notes and fit summaries must describe the
geometry that survives final assembly. A rejected candidate's numeric radius
is not an export dimension. A valid profile can therefore contain analytic
circles/arcs in some rings and a retained polygonal outline in another.

If the retained geometry cannot form a valid profile, the request refuses it
with capture/review guidance. This is not a missing-sheet failure and must not
silently switch to ordinary tracing. Review or retake the source photo, then
trace and build again; the error can also suggest **Simplified** outline detail.
The existing current-project recovery behavior remains;
a failed attempt is not a new accepted model.

The existing [supplied-covariance recovery](anisotropic-corners.md#when-the-corrected-source-ring-is-invalid)
has its own bounded eligibility rules for an invalid corrected ring. The
canonical port does not add polygon cleanup, component deletion or a wider
source-distance allowance to that policy. That recovery can sample the frozen
initial proxy into lines only after its complete-boundary checks and point cap
pass; it does not export the proxy as an analytic circle. Mixed scalar geometry approximations
and undetermined-radius notices also keep their separate meaning.

## Display alignment is a coordinate choice

A detected straight-edge direction can still supply the rigid rotation of the
display image and profile when a fitted ring is retained as line geometry.
The rotation notice says it uses the detected straight-edge direction; it does
not claim the retained outline was accepted as an analytic fit or made exactly
parallel/perpendicular by snapping.

Rotation preserves distances and radii, while axis-aligned width and height
depend on the chosen frame. Snap, equalization and radius notes remain tied to
accepted final geometry. A source-derived alignment notice can therefore appear
when no analytic-line or snapping claim survives.

## Practical checks

Use the [critical arc checklist](exports.md#verify-critical-arc-geometry) when a
radius or chord controls fit. Measure the actual imported CAD geometry and
compare with independent part measurements. Rebuild a critical feature in CAD
from measured dimensions when the trace is only an approximation or its radius
is unresolved.

This change applies to newly assembled reference-sheet fits. A saved recipe or
older export already contains its serialized geometry; reopening it cannot
recover a discarded fitted centre, radius or source witness. Trace the original
photo again when available, rebuild the current model and export fresh files
to use the changed fitting path. Keep the earlier files as separate revisions.

Historical canonical-arc experiments retain their own source revisions,
conditions and outcomes. They are not new runs of this main-based port. Fresh
source-bound replay and integration evidence belong in the port's validation
record; no physical accuracy claim is inferred from the port.
