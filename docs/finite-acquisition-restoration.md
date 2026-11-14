# Historical authoring design for live restoration

This page preserves the **pre-execution authoring snapshot**. For current
status, read the [executed controller method](finite-acquisition-restoration-result.md)
and [first full result](validation/finite-acquisition-restoration-result.md).
The [original published explanation](validation/evidence/acquisition-restoration-20261114/published-authoring-explanation.txt)
is retained verbatim. Statements below about untracked files and pending
execution describe that earlier snapshot.

**Authored local draft; uncommitted and unrun.** This page records the
candidate's design, not a qualified main API or workbench feature. No new
subject import, test collection, software test, solve, point construction or
model call has run. Independent review and a committed combined source
freeze remain pending.

The preceding [standalone correction](finite-acquisition-defect-corrector.md)
lowers actual training cost from 0.302031169350812 to zero on one supplied
synthetic PNG context. That result does not validate a fresh controller.
The latest completed full protocol still has **11/12 matched passes,
exit 1**, with all 24 original cases retained. See the
[complete preceding result](validation/finite-acquisition-defect-corrector.md)
and [full recovery record](validation/finite-acquisition-physical-rounding.md#complete-original-24-case-outcome).

## Source and availability

The separate research checkout remains at committed source
`d986f1f2db12791b96aad21dcc4f1e7977029c40`. Ten new files are untracked:

| Draft files | Intended responsibility |
| --- | --- |
| `backend/finite_acquisition_restoration.py` | Live controller, one optional restoration episode and the shared engine |
| `backend/finite_acquisition_restoration_rational.py` | Bounded rational parsing, certificate checks and nearest physical representation |
| `backend/finite_acquisition_restoration_inward.py` | One inward construction and one nearest tuple |
| `backend/finite_acquisition_restoration_correction.py` | One correction through an actual rejected observation |
| `tests/test_finite_acquisition_restoration_math.py` | Authored mathematical controls |
| `tests/test_finite_acquisition_restoration.py` | Authored controller controls |
| `tests/test_finite_acquisition_restoration_protocol.py` | Authored protocol and provenance controls |
| `studies/verification/finite-acquisition-recovery-restoration-v1.py` | Proposed fresh adapter for all original cases |
| `studies/finite-acquisition-recovery-restoration-v1.json` | Prospective admission |
| `docs/finite-acquisition-restoration.md` in the research checkout | Prospective pre-execution guide, distinct from this published explanation |

The [authoring inventory](validation/evidence/acquisition-restoration-authoring-20261114/manifest.json)
records their current hashes, sizes and untracked state. The old 116
governing inputs retain their bytes. **116 + 10 = 126 prospective path
identities**; this is not a completed freeze, reviewed closure or executed
study. The inventory publishes metadata, not executable draft source.

The intended Python entry point is
`fit_acquisition_segment_restoration(...)`. It is absent from this
main-based runtime and has no HTTP route, browser control or main command.
Formatting, lint and compilation of authored components have been reported;
none establishes functional correctness or a passing new control suite.
No combined test total or pass count is inferred from authored tests.

## Proposed live sequence

The candidate retains the coupled initial phase once, the existing source
event order and final coordinate polish. Only the first eligible exact
certificate in a complete positive-cost PNG fit can consume a restoration
episode. Skipping that episode still consumes the one-episode opportunity;
ordinary affordable event work may continue.

1. Bind the accepted tuple `p0`, its actual source optics `z0`, the current
   seven-column matrix `G`, event bands, physical bounds, spans and exact
   certificate. Reverify the certificate before using its point.
2. Construct one inward rational displacement, select one nearest binary64
   physical tuple `p1` and require the original five representation,
   source/domain and arithmetic-floor gates.
3. Evaluate `p1` through the same live engine. Accept only a fully resolved
   strict actual training-cost decrease relative to `p0`.
4. Only a fully resolved rejected `p1` supplies its actual optical field
   `z1` for one correction. Form `u=(p-p1)/s` and `m1(u)=z1+G u`, retaining
   the original `p0`-normalized domain and spans.
   Division applies only to positive spans; zero-span coordinates stay fixed
   with `u=0` and original normalized displacement `d1=0`.
5. Use the first independent tight normals in original order for one exact
   Gram solve. Verify all rows, select one nearest tuple `p2`, require all
   final gates, then evaluate it at most once. Compare with accepted `p0`.
6. Resume the original event control and coordinate search. An accepted point
   still needs the original completed-search linkage. Zero cost does not
   waive work, provenance, stopping or ambiguity gates.

No saved solution, case identity, reference geometry, reserved dimension,
source-62 rule, corner census or cost-selected fallback may choose a trial.
Code changes are diagnostics; strict qualified actual cost governs acceptance.
The accepted capture stays pinned while a rejected capture is read separately.

The equality and row-space identities establish minimum Euclidean norm of
the normalized correction only for the selected equalities. They do not
establish a full inequality-QP optimum, observation rank, nonlinear convergence, unique geometry or a global
nonlinear error bound. The fixed source guard `2^-12` covers neither general
linearization remainder nor an unknown camera pipeline. Rank, fixed-coordinate,
bit-limit and representation obstructions remain local unknowns.

## Proposed budget and storage policy

The prospective study retains ordinary/default per-fit ceilings of **2,048
evaluations, 1,000,000 cell units and 100,000,000 stage units**, and each
adverse case's lower declared limits. These include the initial phase, event
work, restoration and final polish. They are study ceilings, not the API's
validation maxima for caller-supplied cell/stage budgets. Exact arithmetic
has a 32,768-bit bound and seven coordinates; augmented halfspace rows are capped at 4,096.

Let `S` count finite source-band sides, `R=S+14` include the normalized
box rows, and `A=R+14` include the additional physical-domain rows. Each
invoked mathematical construction proposes a complete tariff

~~~text
T = 65536 + 512*(R + 9*A).
~~~

For `N` source cells, `M` output pixels and kernel entry counts `Ko,Kp`,
one literal PNG forward has declared stage work

~~~text
W = N*(1 + Ko + 4) + M*(16 + Kp).
worst-case episode affordability = [2, 2*N, 2*T + 2*W].
~~~

Affordability is a preflight only. Each invoked math tariff is charged before
rational work, without a refund after failure. Actual trials use the same
engine's normal before-operator accounting. There is no extra incumbent
replay, separate budget, escrow debit or double charging. An unaffordable
optional episode does not by itself exhaust the engine.

This proposed per-operation policy differs from the completed standalone
probe's atomic whole-math-and-pair hold. Its correctness remains unvalidated.
Tariffs are accounting units, not measured time, peak memory or a
bit-complexity theorem.

The draft limits episode capture to two trial calls and **1,048,576 numeric
entries**, with requested capacity `2*(6*N+2*M)` for pre-cast coverage and
available seven-stage captures. Retain unavailable or partially completed
work explicitly. This is not an operating-system memory measurement.

## Required validation

Before any new subject execution, independently review the exact new files,
commit them, and combine-hash the declared 126-path union with Git modes.
Then run the first selected controls once and retain the command, first
output, native handle where returned, log and terminal exit. Only a terminal
pass permits the first full protocol; post-execution fixes require new source
and admission.

The adapter must freshly regenerate all **24 original cases: 12 matched
and 12 adverse**. Preserve targets, observation/reference orders, kernels,
maps, query mask, observed-only preparation, up to four seeds, brightness
rules and adverse work limits. Save the full fit before evaluating truth.
Reserved intensities already affect initialization, so those later residual
checks remain conditional.

Retain refusals, exceptions, unknowns and unstarted rows. Check all known
source paths before and after; a late identity or protocol error must
quarantine both top-level and nested pass labels without deleting raw
diagnostics. Never overwrite or restart a first destination.

No score is promised. Successful controls and a full synthetic protocol would
still leave independent forward/rank qualification, real-camera evidence,
main integration, installed behavior, native slicing and physical fit or
printing to be established separately.
