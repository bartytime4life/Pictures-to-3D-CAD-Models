# Reference scale sensitivity — November 10, 2026

The known-feature controls now expose a collapsible endpoint-placement scenario in the working-image frame. The calculation changes only the assumed endpoint span and holds the measured feature length and pixel outline fixed. Draft scale, scenario shift, and applied model settings remain separate. The scenario survives display-unit changes and never enters a saved project.

Local validation passed **11 calibration, calibration-lifecycle, and sensitivity browser scenarios**, production typecheck/build, Ruff, Prettier, and whitespace checks. Fixed numeric cases verify reciprocal-span bounds, mm/in conversion, zero shift, a span that can collapse to zero, invalid entries, and unchanged project settings/exports. Phone-width checks exercise keyboard input, selected axe A/AA rules, and horizontal overflow. The generated phone screenshot was visually inspected.

Testing found and corrected a unit-switch reset caused by briefly unmounting the scenario during reference conversion. One subsequent calibration run also encountered the preview's missing build output while assets were being rebuilt; the stable completed build was tested again. No browser-test timeout was relaxed.

The combined suite exposed three older lifecycle-test selectors that matched both the outer disclosure summary and the new nested summary, even while hidden. They now select the direct summary child. All four lifecycle scenarios passed again on this PR's source.

The calculations are synthetic scenarios. They establish neither statistical uncertainty nor physical measurement/print accuracy. The [guide](../reference-sensitivity.md) includes the equations, a numeric example, research sources, and their limits. Native screen-reader, slicer, and physical-print checks were not performed. Hosted CI is separate evidence for the PR revision.
