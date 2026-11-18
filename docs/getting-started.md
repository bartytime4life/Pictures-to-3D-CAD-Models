# Getting started

This guide gets you from a running local app to a saved project and a slicer handoff. Start with the demonstration part, then repeat the workflow with your own measured part.

## Install and open

Use Python 3.12, Node.js 22.12 or later, npm and GNU Make. Clone the repository and run setup from its root.

```bash
git clone https://github.com/bartytime4life/Pictures-to-3D-CAD-Models.git
cd Pictures-to-3D-CAD-Models
make setup-app
make doctor
make start
```

Keep the terminal open. Visit [the local application](http://127.0.0.1:8000), or the address printed by the start script when you choose another port. `make setup-app` installs and builds the application. The included OpenSCAD handbook can be read without preparing its separate development environment; use `make setup` when you also want to rebuild or test that handbook. If `python3` points to another version, setup checks `python3.12`, or you can set `PICAD_PYTHON` to an existing Python 3.12 interpreter. See [development and setup](development.md) for platform details.

`make doctor` checks the app environment, required Python packages, built interface, and optional local AI. It prints a next step for any missing requirement and exits successfully when the app requirements are ready. Missing optional Ollama or frontend development tools do not block the built app. This check does not install packages, download models, build CAD, or generate AI responses. For JSON output, run `./scripts/doctor.sh --json`; use `--skip-ai` to skip the loopback Ollama metadata request.

A remote backend runs on the remote machine: use its supported port-forwarding mechanism. Your laptop's localhost does not automatically reach that backend.

## Choose your task

The app opens on **Start** without creating a CAD job. Choose **Design a flat part** to combine common shapes, **Trace a photo into CAD** to open your measured photograph, or **Make a relief or lithophane** to create depth from a picture. Supporting tools explain their own AI requirements before you enter them.

**Saved flat-part projects** opens this browser's project snapshots. **Open a downloaded project** accepts a portable recipe JSON in the photo-or-project chooser. A source photo collection lives separately in **Photo library**. On phones and tablets, use the **Workspace** picker to change tools; larger screens show tabs. Navigation retains drafts in the current page.

Expand **Local setup → Setup details** for missing requirements and suggested commands. It checks installed requirements, not the correctness of a CAD export or AI answer.

## Learn with the sample

1. On **Start**, select **Try the flat-part sample**. The mounting-plate sample is traced and built with demonstration dimensions: 80 mm reference width and 4 mm thickness.
2. Compare the cyan source outline and holes with the 3D solid. Use the available views and reset control to inspect the result.
3. Under **Quick edit**, enter a target width of 100 mm. Leave the field or press Enter to commit. The target height changes proportionally; the measured reference width remains 80 mm.
4. Select **Update model** in the CAD panel or **Update preview** in **Next step**. Until a fresh build succeeds, the old result remains marked outdated and new exports are unavailable.
5. Use Undo or Redo to restore design settings, then rebuild the chosen version. History does not restore expired export files.

The sample demonstrates the workflow; it is not a measurement of your part.

## Prepare a print plan

1. Select **Prepare for slicing**. Choose **Quick prototype**, **Everyday** or **Fine surface** as a process starting point.
2. Review layer height, walls, infill, supports and adhesion. These values become notes to enter in the receiving slicer; they do not generate toolpaths here.
3. Open **Printer & split settings**. Select the intended printer/nozzle or enter custom X/Y/Z bounds and margin. Check the actual machine and native profile independently.
4. Build the updated plan. Inspect each piece in the bed view. Change the preview turn or toggle grid, margin and dimensions; **Reset view** restores the suggested orientation when available, otherwise the original angle. These controls do not rotate the exported model.
5. Choose **Review slicer handoff** and a slicer: Bambu Studio, PrusaSlicer, QIDI Studio, OrcaSlicer or UltiMaker Cura.
6. Download the ZIP, extract it, import its 3MF as geometry, and follow the included process plan and instructions. Choose native machine/material settings, slice, inspect layers and save a native slicer project there.

For split output, arrange the individual part files separately. The combined 3MF preserves assembly positions; it is not a prepared multi-object plate. See [slicer integration](slicers.md).

## Use your own photograph

Photograph one flat, constant-thickness object from the front with its full outline visible. Use diffuse light and a contrasting background. Avoid a hand or another object covering the silhouette. Read the [capture guide](capture-guide.md) for examples and limitations.

Choose a source scale:

- Enter a measured full outside width, plus the measured thickness.
- Use a known feature or suitable measured reference, place both endpoints carefully, and verify its actual length. A common-object suggestion supplies a convenient starting value, not a measurement of your particular object.
- For a suitable paper capture, explicitly select the reference sheet and include its full boundary. Read [reference-sheet tracing](reference-sheet.md) before relying on that correction.

Review holes and the outer contour before building. A second independent dimension helps reveal perspective or scale errors. Adjust the capture or reconstruct critical features in a CAD editor when the image cannot establish them.

Optional **Remove background** produces a transparent PNG from the current reviewed outline, keeping holes transparent. It does not change the tracing settings, geometry or original source file.

## Save before leaving

Choose **Project library → Save current snapshot** in Flat part to keep a version in the current browser. Open the saved entry later to rebuild it or record the outcome of a print. See [saving snapshots and recording prints](workflows.md#save-snapshots-and-record-prints).

Use **Save project** or **Download recipe** from a saved snapshot to download portable JSON. The file carries the outline and editable settings. Keep the original photograph alongside it and download any geometry files you plan to use.

Navigation within the page keeps visited studio drafts in memory. Reloading or closing the page clears those drafts. To resume, use **Start → Saved flat-part projects → Open in workbench**, or **Start → Open a downloaded project → Browse files**. The replacement becomes current after it builds successfully. Temporary geometry exports expire, even for a saved project.

Knowledge notes and Science scenarios have their own storage and export controls. They are not included automatically in the CAD recipe. See [workflows](workflows.md) and [troubleshooting](troubleshooting.md).
