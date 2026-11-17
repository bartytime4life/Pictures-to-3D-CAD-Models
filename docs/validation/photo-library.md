# Photo library validation

Recorded November 16, 2026, for the candidate on branch `claude/dinov3-vision`. It was
developed and measured on main `40cfbe4`, then rebased onto `c2a8fea` (#155), which
changed the shadow solver and none of this work's files. The figures describe that
source on one computer. They are not evidence of accuracy on photographs of real
parts, of deployment, or of any print.

Machine: AMD Ryzen 9 9950X (16 cores, 32 threads), 121 GB memory, NVIDIA GeForce RTX
5080 (16 GB), PyTorch 2.15.0+cu132, DINOv3 code at `6876159a11b4`. The computer was
running other work during the timing runs (load average 13 to 35), so the rates are
lower bounds for it.

## Evidence classes

| Class | What was done | What it shows |
| --- | --- | --- |
| Rendered benchmark | Drawings of 14 flat parts on 8 procedural surfaces with known identity, outline and blur, indexed by the real pipeline and model | How the pipeline behaves on these shapes and variations |
| Real files, counts only | 6,784 pictures from two personal folders indexed read-only; only counts and times were read | That mixed real files decode and index, and how fast |
| Unit and route tests | Numerical steps, pipeline, storage rules and HTTP routes with a stand-in for the network | That the integration behaves around the model |
| Browser scenarios | The interface against a running service | That the workflows work end to end |

Nothing here measures accuracy on photographs of real parts. That needs photos of
known parts, as the [photo benchmark](../photo-benchmark.md) does for tracing.

## Rendered benchmark

`scripts/vision_scenes.py` draws each part at a random rotation, size (a quarter to
three fifths of the frame width) and place, with a soft contact shadow, a random
perspective, uneven light, Gaussian blur of 0.6 to 2.2 px, sensor noise and JPEG
quality 72 to 94. Backgrounds rotate so every part appears on several surfaces and
every surface carries several parts. The generator shares no code with the workbench
or the vision engine.

Each set has 8 shots per part. Two shots of each part also get an exact copy, a copy
re-saved at JPEG quality 60 and a half-size copy.

Protocol: thresholds were chosen on seven parts (cross, flange, gusset, l-bracket,
oval-gasket, slot-plate, t-bracket; seed 2026) and scored on the other seven (d-plate,
gear, hex-plate, mounting-plate, ring-gasket, star-washer, u-clip; seed 4051). The
"all 14" rows index all fourteen parts together, which is harder because more parts can
be confused. They include the calibration parts and are not held out.

Reproduce with `make vision-benchmark`,
`.venv/bin/python scripts/vision_benchmark.py --calibrate` and `--all`, setting
`PICAD_VISION_MODEL` for one model. The JSON reports behind the tables are in
[`docs/benchmarks/photo-library/`](../benchmarks/photo-library/).

### Results

Subject: found / shots, mean region overlap (intersection over union at the 28 × 28
grid against the true outline), mean bounding-box overlap, and boxes overlapping less
than half. Matching: share of shots whose nearest other shot is the same part, and mean
average precision, for the subject vector and for the whole-picture vector. Groups:
of all pairs placed in one group, the share truly the same part (precision); of all
true same-part pairs, the share placed together (recall); and groups found. Best
shot: groups whose best shot is the truly most detailed (rendered long side over
rendered blur), and within the top three.

| Model | Set | Subject found | Region | Box | Box < 0.5 | Subject first | Subject mAP | Whole first | Whole mAP | Group precision | Group recall | Groups | Copies found | Best shot | Top three |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ViT-B/16 | held out | 56/56 | 0.73 | 0.87 | 0 | 1.000 | 0.994 | 0.857 | 0.888 | 1.00 | 1.00 | 7 of 7 | 42/42 | 3/7 | 3/7 |
| ViT-B/16 | all 14 | 112/112 | 0.72 | 0.86 | 0 | 1.000 | 0.969 | 0.795 | 0.798 | 0.76 | 0.98 | 13 of 14 | 84/84 | 9/13 | 12/13 |
| ViT-L/16 | held out | 56/56 | 0.69 | 0.81 | 2 | 1.000 | 0.972 | 0.839 | 0.864 | 1.00 | 0.86 | 8 of 7 | 42/42 | 5/8 | 5/8 |
| ViT-L/16 | all 14 | 112/112 | 0.68 | 0.81 | 4 | 1.000 | 0.924 | 0.804 | 0.771 | 0.81 | 0.76 | 18 of 14 | 84/84 | 16/18 | 17/18 |
| ViT-S+/16 | held out | 56/56 | 0.70 | 0.83 | 2 | 1.000 | 0.970 | 0.821 | 0.861 | 0.75 | 0.96 | 6 of 7 | 42/42 | 2/6 | 3/6 |
| ViT-S+/16 | all 14 | 112/112 | 0.69 | 0.83 | 7 | 0.964 | 0.887 | 0.786 | 0.762 | 0.74 | 0.86 | 15 of 14 | 84/84 | 12/15 | 14/15 |
| ViT-S/16 | held out | 56/56 | 0.74 | 0.87 | 0 | 1.000 | 0.991 | 0.911 | 0.912 | 1.00 | 0.96 | 7 of 7 | 42/42 | 3/7 | 3/7 |
| ViT-S/16 | all 14 | 112/112 | 0.73 | 0.87 | 3 | 0.982 | 0.907 | 0.821 | 0.792 | 0.79 | 0.89 | 13 of 14 | 84/84 | 9/13 | 12/13 |

No copy set mixed two different shots in any run.

What the table supports:

- Pooling the patch vectors over the found subject matches parts better than the
  model's whole-picture vector in every row: for ViT-B/16, 1.000 against 0.857 for the
  first match on the held-out parts, because the whole-picture vector also describes
  the surface the part lies on.
- ViT-B/16 is the default on a graphics card. It equals or beats ViT-L/16 on every
  column but best shot, and runs about three times faster.
- Groups merge parts that look alike. With all fourteen parts, ViT-B/16 puts the
  L-bracket and the T-bracket in one group (13 groups, precision 0.76). No rule tried
  separated them at a usable recall.
- The best shot is right less often than not on the held-out set (3 of 7 for ViT-B/16)
  and more often with all parts (9 of 13). It is a ranking aid. The subject's span
  comes from a 28 × 28 grid and is too coarse to rank shots of similar size.

### Thresholds

For each model, every link threshold from 0.76 to 0.92 was tried with every split
threshold at or below it on the calibration parts. Of the pairs within 0.02 of the best
pair F1, the strictest was taken, because a group that wrongly merges two parts hides
one of them. The look-alike threshold, 0.96 for all models, lies between the largest
cosine of two different shots and the smallest cosine of a re-saved or half-size copy.

| Model | Link | Split | Calibration precision | Calibration recall | Best F1 in grid | Largest different-shot cosine | Smallest copy cosine |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ViT-B/16 | 0.84 | 0.80 | 0.747 | 0.964 | 0.860 | 0.932 | 0.979 |
| ViT-L/16 | 0.82 | 0.78 | 1.000 | 0.776 | 0.874 | 0.934 | 0.970 |
| ViT-S+/16 | 0.84 | 0.80 | 0.747 | 0.964 | 0.842 | 0.935 | 0.981 |
| ViT-S/16 | 0.84 | 0.80 | 0.747 | 0.964 | 0.842 | 0.946 | 0.985 |

The calibration precision of 0.747 is the L-bracket and T-bracket sharing a group.

## Edge blur

`tests/synthetic.py` renders the reference-sheet plate with a chosen sensor blur. Two
noise seeds each, 1600 × 1200 pixels:

| Rendered blur (px) | 0.5 | 1.0 | 1.5 | 2.0 | 3.0 | 4.0 |
| --- | --- | --- | --- | --- | --- | --- |
| Measured (px) | 0.76, 0.86 | 1.27, 1.28 | 1.65, 1.65 | 2.18, 2.18 | 3.16, 3.17 | 4.12, 4.13 |

The measured value exceeds the rendered one by the renderer's own pixel integration,
resampling and JPEG, about 0.8 px in quadrature. Enlarged 2.52 times to 12 megapixels,
the 2.0 px render read 5.15 px against 5.49 expected: a reading above about five
measured pixels is cut short by the 12-pixel profile. A picture of noise alone gives
no reading.

On the benchmark, the rank correlation between the rendered blur and the measured
blur was 0.75 (held out) and 0.66 (all 14) for the whole picture, and 0.83 and 0.84
when read on the subject alone. Background texture carries its own edges, which is why
the subject reading is used for the best shot.

## Throughput

| Collection | Photos | Read | Describe | Whole crunch |
| --- | --- | --- | --- | --- |
| Two personal folders, mostly small PNG, mean 0.2 MP, largest 67 MP | 6,784 | 575 per second | 183 per second | 52.5 s (129 per second) |
| Rendered 12.2 MP JPEGs, 1.6 GB | 960 | 102 per second | 174 per second | 18.3 s (53 per second) |

The whole crunch includes about 3 s to start the model. Organizing 6,784 photos took
0.7 s. In that library a similar-photo query took 6 ms, a sorted page 41 ms, and a
rescan with nothing changed 0.9 s. Its storage was 150 MB. All 6,784 files decoded;
2,004 had too few clear edges for a blur reading (icons and small graphics) and 7 had
no separable subject. It found 1,854 exact copies, 1,146 look-alikes and 696 groups.
Nothing in those pictures was inspected, so the quality of those groups is unknown.

HEIC files are decoded in a child process each, at full size, and will be slower than
JPEG. That rate was not measured.

## What was tried and not adopted

The overlap figures in this section are from an earlier version of the benchmark
renders (112 shots, same parts and surfaces) and are comparable with each other.

- **Subject from the image border.** Calling a patch background when it resembles a
  border patch follows a position pattern in the features of plain surfaces. Mean
  region overlap 0.34 to 0.61, against 0.72 for the plane fit.
- **Subject from the class token.** The cosine between each patch and the class token
  outlines the part crisply on plain surfaces (0.53 to 0.67 overall) but inverts on a strongly
  textured one, where the token describes the surface.
- **First principal component, and a normalized cut** of the patch similarity graph
  (as implemented here, with one similarity threshold): 0.28 to 0.39 and 0.10 to 0.13.
- **Groups by shared neighbours.** Linking photos whose neighbour lists overlap
  separated the two brackets (precision 1.00, recall 0.93) only with exactly 8 shots
  per part. With 3 or 4 shots per part precision fell back to 0.70. Not adopted.
- **ViT-H+/16** matched worse than ViT-B/16 on an early run (first match 0.955 against
  1.000) at a seventh of the speed, and is not connected.
- **The model in 16-bit throughout.** ViT-L/16 returned invalid values. The model now
  stays in 32-bit and runs under 16-bit autocast; class tokens then agree with 32-bit
  ones to a cosine of 0.99999.

## Faults found while building it

- The first blur estimator read an impossibly sharp 0.1 px on faint edges in noise,
  and that photo then won "best shot". The slope is now taken from the rise across
  ±d, and a reading below the smoothing applied is discarded.
- Projecting an 8-bit picture onto the contrast direction clipped at 255 and halved
  every blur reading. Found by re-running the known-blur renders after the change.
- Edges between a red part and a green surface of equal brightness had no reading on
  brightness alone. Blur is now measured along the colour direction of most contrast.
- Reading 12-megapixel JPEGs ran at 27 to 30 a second whatever the number of reader
  processes. Per-stage times rose in proportion to the process count: the limit was
  memory traffic. Measuring blur in small full-resolution windows, and decoding large
  JPEGs at half scale, raised it to 102 a second.
- PyTorch's hub loader copied every weight file into its own cache. Weights are now
  loaded directly with `weights_only=True`.
- Two identical uploads sent at the same moment were both stored. Uploads are now
  taken one at a time.
- Opening a group from the Groups view showed an empty grid. Found by the browser test.
- A reader pool whose processes never answer would have held the crunch, and Cancel,
  for ever. Seen when another tool ran the tests in a sandbox that froze the pool. The
  read stage now gives up after 180 s without any reader returning, stops the readers
  and leaves the unread photos for the next crunch.
- A web page on another site could have posted files into a library on this computer,
  because a multipart upload needs no permission from the browser. Routes that change
  the library now refuse a request whose `Origin` host is not the one addressed.

## Checks run

On the candidate before it was rebased, with the vision model installed:

- **Python:** the complete suite, 1,525 passed and 2 skipped in 483 s. It included 27
  library tests and 21 vision tests; one of the vision tests runs the real model. A
  28th library test, for readers that stop responding, was added afterwards, and the
  two suites then passed again: 49 passed.
- **Browser:** the complete suite against a dedicated server with an empty library,
  92 passed and 1 skipped in 7.1 minutes. The skipped scenario needs the separate AI
  depth model. Five scenarios are the library's; they passed three more times in a row.
- **An earlier full browser run failed one existing scenario:** with a fourth header
  tab, the tabs ran past the edge of a 320 px screen. Tab labels now sit under their
  icons at 400 px and below, and the project name keeps its room between 1251 and
  1450 px. The rerun above includes that fix.
- **Build and lint:** TypeScript and the production build, Ruff on `backend`, `scripts`
  and `tests`, Prettier on the frontend and browser tests, and `git diff --check`.
- **Documentation:** relative links, heading anchors and table column counts of the
  ten touched pages were checked by script.
- **Install script:** `make vision-model WEIGHTS=...` was run once from nothing on this
  computer: it built the environment, verified and linked four weight files and started
  ViT-B/16 on the graphics card.

After the rebase, the library, vision, shadow-optimality, backend, depth and relief
suites passed again (217 passed, 2 skipped), as did the library, workbench and relief
browser scenarios (22 passed, 1 skipped), the build and lint. The complete suites were
not repeated locally after the rebase; the pull request's CI runs them.

CI runs without the vision model: the real-model Python test and the real-model browser
scenario are skipped there, and the rest run with the stand-in or without features.

The browser scenarios add photos through the page and through a folder, check the
catalogue, the copy handling, sorting and filtering, the CSV export, the hand-off to
both studios, the messages without folder access or the model, a mocked crunch in
progress, and, with the model installed, grouping and similar-photo search on 24
rendered shots of four parts. Accessibility is checked with axe in three of them.

## Limits of this record

- Every quality figure is from rendered drawings. Real photographs have materials,
  reflections, clutter and parts that differ only in dimensions.
- The calibration and evaluation parts come from one generator and share its style.
- Fourteen parts and 112 shots are small samples: one photo moves a group score by
  several hundredths.
- Throughput was measured once per collection on one loaded computer.
