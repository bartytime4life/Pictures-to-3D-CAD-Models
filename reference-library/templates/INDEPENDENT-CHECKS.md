# Independent measurement checks

Part: __________  Model revision: __________  Check date/operator: __________

Record physical checks of a specific model revision, using `independent-checks.csv` for results. See handbook section 18. Blank means unknown.

## Reserve the checks before modeling

- [ ] Choose critical check dimensions in several directions and locations before modeling.
- [ ] Keep those checks separate from dimensions used to set scale, fit features, or choose alignment.
- [ ] Record the physical reference method and evidence file. A second reading from the same unqualified image is not an independent physical reference.
- [ ] Record uncertainty or a concrete limitation for each reference measurement. Instrument resolution alone is insufficient.
- [ ] State the tolerance or functional criterion and the decision rule before inspecting model results.

## Freeze the model before comparison

Model/exchange file: __________  File hash or retained copy: __________

Transform/scale file: __________  Units and datums: __________

- [ ] Preserve the exact model revision and scale/alignment transform being checked.
- [ ] Keep reference measurements unchanged during this comparison.
- [ ] Record each model dimension and signed difference as `model_mm - reference_mm`.
- [ ] Review every reserved check; record missing or inaccessible measurements as `not_tested`.
- [ ] Use `pass`, `fail`, or `unresolved` only under the recorded decision rule. A result near a tolerance limit may need a better measurement.

## If a check leads to a correction

Keep the earlier result. Mark `used_to_adjust_model` as `yes`, describe the correction, and change its `role` to `development`. It no longer independently checks the revised model. Save a new revision and obtain fresh checks where practical; otherwise report independent evaluation as incomplete.

Final check set: __________  Unresolved features: __________

Outcome and scope: __________  Next physical fit/print test: __________

Passing selected dimensions does not establish the entire surface, printer performance, strength, or mechanism behavior.
