export type Guide = {
  id: string;
  category: string;
  title: string;
  summary: string;
  steps: string[];
  assumptions: string;
  doc: string;
  action: { label: string; href: string };
  sources?: { label: string; url: string }[];
};
export const GUIDES: Guide[] = [
  {
    id: 'capture',
    category: 'Getting started',
    title: 'Capture a traceable flat part',
    summary: 'Give the outline, reference and through holes a clear view.',
    steps: [
      'Choose a flat, constant-thickness part such as a plate, gasket or spacer. A single photo cannot reveal hidden surfaces.',
      'Place the part against a contrasting, even background. Include the whole outline and keep through holes visible.',
      'Photograph straight-on, keep the camera steady and avoid glare or a strong cast shadow along the edge.',
      'Record a real dimension and the thickness separately. Import the photo, then review the traced outer boundary and holes before building.',
    ],
    assumptions:
      'The flat-part workflow extrudes a visible profile. Perspective, lens distortion and obscured edges can change the trace. Use a reference sheet when its correction assumptions fit your capture.',
    doc: 'capture-guide',
    action: { label: 'Open the flat-part workbench', href: '#workbench' },
  },
  {
    id: 'measurement',
    category: 'Measurement',
    title: 'Measure from a known object',
    summary: 'Turn a visible reference into a pixel-to-length scale.',
    steps: [
      'Place a measured object beside the part in the same plane as the outline. A larger, clear reference makes endpoint placement easier.',
      'Open Use a known feature. Enter your measured length, or choose a nominal U.S. coin diameter and verify the actual coin.',
      'Mark two visible endpoints. For a coin diameter, use opposite edges through its center. The app does not detect or identify the coin for you.',
      'Review the scale and outside width, then choose Apply reference scale. Check another independently measured dimension before making the part.',
    ],
    assumptions:
      'Uniform scale assumes a shared image plane and a near front-on photograph. Coin presets are nominal sizes. Saved recipes retain the numerical length, endpoints and image dimensions; they do not claim automatic recognition.',
    doc: 'reference-sensitivity',
    action: { label: 'Explore pixel scale', href: '#science?experiment=scale' },
    sources: [
      {
        label: 'U.S. Mint: nominal coin dimensions',
        url: 'https://www.usmint.gov/learn/coins-and-medals/circulating-coins/coin-specifications',
      },
      {
        label: 'OpenCV: camera projection and distortion',
        url: 'https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html',
      },
    ],
  },
  {
    id: 'sensitivity',
    category: 'Measurement',
    title: 'Read sensitivity without overstating accuracy',
    summary: 'Separate an endpoint scenario from a full measurement uncertainty.',
    steps: [
      'Start with the reference length and marked pixel span. Scale is length divided by pixels; multiply by the outline span for part width.',
      'In Science lab, vary the assumed shift per endpoint. The longer-span case makes the calculated part smaller; the shorter-span case makes it larger.',
      'Compare the result with independent measurements. Check the photograph, trace and measurement method before accepting a dimension.',
    ],
    assumptions:
      'Endpoint sensitivity excludes other error sources. It is not a confidence interval. A full uncertainty analysis must consider significant sources, their sensitivity and any covariance.',
    doc: 'reference-sensitivity',
    action: { label: 'Open Science lab', href: '#science?experiment=scale' },
    sources: [
      {
        label: 'NIST: propagation of uncertainty',
        url: 'https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-law-propagation-uncertainty',
      },
    ],
  },
  {
    id: 'background',
    category: 'Getting started',
    title: 'Remove the photo background',
    summary: 'Make an optional transparent cutout from the reviewed silhouette.',
    steps: [
      'Trace the flat part and inspect its outer boundary and through holes. Use Adjust outline if the trace misses the edge.',
      'Choose Remove background beneath the source image. The checkerboard indicates transparent areas.',
      'Switch between Original and Background removed. Save transparent PNG to keep a separate image.',
    ],
    assumptions:
      'The cutout uses the current outline and working-image pixels, including a corrected reference-sheet image when present. It preserves your original photo and model measurements. It is not arbitrary-scene AI segmentation; changing the trace clears the cutout.',
    doc: 'workflows',
    action: { label: 'Open the source workbench', href: '#workbench' },
  },
  {
    id: 'editing',
    category: 'Getting started',
    title: 'Edit size without losing your reference',
    summary: 'Keep source measurements and intentional design scaling distinct.',
    steps: [
      'Set the measured reference width and thickness first. Build the solid and inspect it in the CAD viewport.',
      'Use Quick edit for target width or thickness. Width scales XY together so the source proportions remain linked.',
      'Use Undo and Redo for design and print-setting changes. Source, trace or reference changes start a fresh design history.',
      'Rebuild after an edit. Export only when the current preview matches the settings you want.',
    ],
    assumptions:
      'The workbench edits a traced profile extrusion and its design settings. It is not a general sculpting or feature-based CAD editor. Export editable CAD or source files for broader work.',
    doc: 'print-planning',
    action: { label: 'Edit in the workbench', href: '#workbench' },
  },
  {
    id: 'slicing',
    category: 'Printing',
    title: 'Prepare a dependable slicer handoff',
    summary: 'Review geometry, printer envelope and the process plan separately.',
    steps: [
      'Build the current model, then choose Prepare for slicing. Review nozzle, layer height, walls, infill, supports and adhesion.',
      'Inspect each piece on the bed preview. A footprint that fits the envelope still needs review for placement, supports and travel clearance in the slicer.',
      'Choose a supported slicer and download its handoff ZIP. Import the 3MF geometry and review the included process-plan.json.',
      'Select the actual printer, nozzle, filament and process profile in the native slicer. Slice there and inspect its layers before printing.',
    ],
    assumptions:
      'The bed preview is one piece at a time, not an arranged plate or toolpath simulation. A geometry handoff does not silently configure a native slicer. Executable detection and launch requests do not prove successful import or printing.',
    doc: 'slicers',
    action: { label: 'Prepare a model', href: '#workbench' },
    sources: [
      {
        label: 'Prusa: layers and perimeters',
        url: 'https://help.prusa3d.com/article/layers-and-perimeters_1748',
      },
    ],
  },
  {
    id: 'fit',
    category: 'Printing',
    title: 'Use a coupon to investigate fit',
    summary: 'Compare a CAD dimension with a measured printed result.',
    steps: [
      'Make a small coupon using the same material, orientation, printer and process settings intended for the part.',
      'Measure the coupon hole and mating shaft. Record the CAD hole dimension and whether your intended clearance is diametral or radial.',
      'Use Measured fit in Science lab to explore a correction under an additive-bias assumption. Positive diametral clearance is twice the radial gap.',
      'Print and measure a second coupon before transferring the change to a full part. Keep both records and note any process changes.',
    ],
    assumptions:
      'A single measurement does not establish a universal shrinkage factor, a fit tolerance or mechanical strength. Negative clearance represents interference and does not predict assembly forces.',
    doc: 'engineering-model',
    action: { label: 'Open the fit experiment', href: '#science?experiment=fit' },
  },
  {
    id: 'relief',
    category: 'Getting started',
    title: 'Choose relief for a picture surface',
    summary: 'Use a photograph as a surface rather than a flat-part outline.',
    steps: [
      'Open Relief for a raised image or a lithophane illuminated from behind. Start with a sample to inspect the available controls.',
      'Set the intended width and minimum/maximum thickness. The picture supplies surface variation; physical dimensions come from your settings.',
      'Review the preview and numerical checks. Export STL or 3MF for a slicer, or the Blender scene for further editing.',
    ],
    assumptions:
      'Brightness-derived relief is not recovered physical shape. Optional AI depth is a relative estimate and needs separately installed model files; it does not establish metric depth.',
    doc: 'relief',
    action: { label: 'Open Relief studio', href: '#relief' },
  },
  {
    id: 'recovery',
    category: 'Recovery',
    title: 'Recover a project and its evidence',
    summary: 'Keep editable inputs distinct from temporary model downloads.',
    steps: [
      'Save the project recipe after measuring and editing. It includes the outline, dimensions and supported settings; it does not embed the photo.',
      'Retain the original photo separately. Restoring a recipe rebuilds its model, while photo-dependent tools require the original image.',
      'If temporary exports expire, rebuild the current model. If a trace fails, improve the input or outline settings and try again.',
      'Export your Knowledge notebook and Science scenarios before clearing browser data. Their storage belongs to this browser and origin.',
    ],
    assumptions:
      'Browser storage is convenient, not a backup. Private browsing, storage limits, a different port or clearing site data can remove or separate your notebook. Download an explicit JSON backup.',
    doc: 'troubleshooting',
    action: { label: 'Return to your model', href: '#workbench' },
  },
];

export type Notebook = {
  format: 'pictures-to-cad-notebook';
  version: 1;
  pins: string[];
  notes: Record<string, string>;
};
export const EMPTY_NOTEBOOK: Notebook = {
  format: 'pictures-to-cad-notebook',
  version: 1,
  pins: [],
  notes: {},
};
export const NOTEBOOK_KEY = 'pictures-to-cad.notebook.v1';
export const LOCAL_GUIDES: Record<string, string> = {
  'capture-guide': 'capture',
  'reference-sensitivity': 'science',
  'print-planning': 'workflows',
  'engineering-model': 'science',
};
export function parseNotebook(value: unknown): Notebook {
  const data = value as Partial<Notebook> | null;
  if (
    !data ||
    data.format !== EMPTY_NOTEBOOK.format ||
    data.version !== 1 ||
    !Array.isArray(data.pins) ||
    !data.notes ||
    typeof data.notes !== 'object' ||
    Array.isArray(data.notes)
  )
    throw new Error('Choose a Pictures to CAD notebook, version 1.');
  const ids = new Set(GUIDES.map((guide) => guide.id));
  if (data.pins.some((id) => typeof id !== 'string' || !ids.has(id)))
    throw new Error('The notebook contains an unknown pinned guide.');
  const notes: Record<string, string> = {};
  for (const [key, value] of Object.entries(data.notes)) {
    if (!ids.has(key) || typeof value !== 'string' || value.length > 10_000)
      throw new Error(
        'Notebook notes must belong to a guide and contain at most 10,000 characters each.',
      );
    notes[key] = value;
  }
  return { format: EMPTY_NOTEBOOK.format, version: 1, pins: [...new Set(data.pins)], notes };
}
export function searchGuides(query: string, category = 'All guides', pins?: string[]) {
  const words = query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  return GUIDES.filter(
    (guide) =>
      (category === 'All guides' || guide.category === category) &&
      (!pins || pins.includes(guide.id)) &&
      words.every((word) =>
        [guide.title, guide.summary, guide.category, guide.assumptions, ...guide.steps]
          .join(' ')
          .toLocaleLowerCase()
          .includes(word),
      ),
  );
}
