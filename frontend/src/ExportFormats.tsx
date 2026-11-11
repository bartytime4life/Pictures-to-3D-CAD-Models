import { DownloadSimple, SpinnerGap } from '@phosphor-icons/react';
import type { ExportKind, ModelResult } from './types';

type Format = { type: ExportKind; label: string; description: string; suffix: string };

export default function ExportFormats({
  model,
  downloading,
  onDownload,
}: {
  model: ModelResult;
  downloading: string | null;
  onDownload: (kind: ExportKind) => void;
}) {
  const primary: Format[] = [
    { type: 'step', label: 'STEP', description: 'CAD solid for CAD applications', suffix: '.step' },
    { type: 'stl', label: 'STL', description: 'Triangle mesh for 3D printing', suffix: '.stl' },
    ...(model.downloads['3mf']
      ? [
          {
            type: '3mf' as const,
            label: '3MF',
            description: 'Millimeter mesh with separate objects for split parts',
            suffix: '.3mf',
          },
        ]
      : []),
    ...(model.downloads.parts
      ? [
          {
            type: 'parts' as const,
            label: 'Parts ZIP',
            description: 'Individual STEP and STL files for each built part',
            suffix: '.zip',
          },
        ]
      : []),
  ];
  const additional: Format[] = [
    { type: 'dxf', label: 'DXF', description: 'Flat outline for 2D workflows', suffix: '.dxf' },
    ...(model.downloads.svg
      ? [
          {
            type: 'svg' as const,
            label: 'SVG',
            description: 'Flat outline for laser cutters and vector editors',
            suffix: '.svg',
          },
        ]
      : []),
    ...(model.downloads.pdf
      ? [
          {
            type: 'pdf' as const,
            label: 'PDF',
            description: 'Drawing to print at 1:1 and lay the part on',
            suffix: '.pdf',
          },
        ]
      : []),
    {
      type: 'scad',
      label: 'OpenSCAD',
      description: 'Editable profile extrusion with the current holes and design',
      suffix: '.scad',
    },
  ];
  function option(format: Format) {
    return (
      <button
        key={format.type}
        className="export-row"
        disabled={!!downloading}
        onClick={() => onDownload(format.type)}
      >
        <span className="format-name">{format.label}</span>
        <span className="format-description">
          {format.description}
          <small>{format.suffix} · millimeters</small>
        </span>
        {downloading === format.type ? (
          <SpinnerGap size={23} className="spinner" />
        ) : (
          <DownloadSimple size={23} />
        )}
      </button>
    );
  }
  return (
    <>
      <section className="file-formats" aria-label="CAD and mesh downloads">
        <h3>CAD &amp; 3D printing</h3>
        <p>
          Choose STEP to continue in CAD, or a mesh for your slicer. For split output, Parts ZIP
          keeps each piece separate.
        </p>
        <div className="export-options">{primary.map(option)}</div>
      </section>
      <details className="additional-formats">
        <summary>Drawings &amp; source files</summary>
        <p>Choose a flat outline, a drawing to print at 1:1, or editable OpenSCAD source.</p>
        <div className="export-options">{additional.map(option)}</div>
      </details>
    </>
  );
}
