export type LabTool = 'scale' | 'layers' | 'fit';

/** Only explicit experiment links change a kept-alive studio's selected tool. */
export function experimentFromHash(hash: string): LabTool | null {
  const separator = hash.indexOf('?');
  if (separator < 0 || hash.slice(0, separator) !== '#science') return null;
  const experiment = new URLSearchParams(hash.slice(separator + 1)).get('experiment');
  return experiment === 'scale' || experiment === 'layers' || experiment === 'fit'
    ? experiment
    : null;
}

/** Representative bands stay inside the SVG and above its bed at y=185. */
export function layerBands(count: number) {
  if (!Number.isInteger(count) || count < 1) throw new Error('Layer count must be positive.');
  const bands = Math.min(count, 26);
  const pitch = 140 / bands;
  return Array.from({ length: bands }, (_, index) => ({
    y: 185 - (index + 1) * pitch,
    height: 0.88 * pitch,
    first: index === 0,
  }));
}

export type LabScenario = {
  format: 'pictures-to-cad-science';
  version: 1;
  active: LabTool;
  scale: { knownMm: number; referencePx: number; outlinePx: number; endpointShiftPx: number };
  layers: { heightMm: number; layerMm: number; firstLayerMm: number; nozzleMm: number };
  fit: { cadHoleMm: number; measuredHoleMm: number; shaftMm: number; clearanceMm: number };
};

export const LAB_DEFAULTS: LabScenario = {
  format: 'pictures-to-cad-science',
  version: 1,
  active: 'scale',
  scale: { knownMm: 24.26, referencePx: 200, outlinePx: 650, endpointShiftPx: 1 },
  layers: { heightMm: 4, layerMm: 0.2, firstLayerMm: 0.2, nozzleMm: 0.4 },
  fit: { cadHoleMm: 10, measuredHoleMm: 9.8, shaftMm: 10, clearanceMm: 0.2 },
};

function bounded(value: number, min: number, max: number, label: string) {
  if (!Number.isFinite(value) || value < min || value > max)
    throw new Error(`${label} must be between ${min} and ${max}.`);
}

export function scaleScenario(input: LabScenario['scale']) {
  bounded(input.knownMm, 0.001, 2000, 'Known length (mm)');
  bounded(input.referencePx, 1, 1_000_000, 'Reference span (px)');
  bounded(input.outlinePx, 1, 1_000_000, 'Outline span (px)');
  bounded(input.endpointShiftPx, 0, 1000, 'Shift per endpoint (px)');
  const { knownMm: known, referencePx: span, outlinePx: outline, endpointShiftPx: shift } = input;
  if (span <= 2 * shift)
    throw new Error('The reference span must exceed twice the endpoint shift.');
  return {
    mmPerPixel: known / span,
    widthMm: (outline * known) / span,
    lowMm: (outline * known) / (span + 2 * shift),
    highMm: (outline * known) / (span - 2 * shift),
  };
}

export function layerScenario(input: LabScenario['layers']) {
  bounded(input.heightMm, 0.01, 2000, 'Part height (mm)');
  bounded(input.layerMm, 0.01, 2, 'Regular layer height (mm)');
  bounded(input.firstLayerMm, 0.01, 2, 'First layer height (mm)');
  bounded(input.nozzleMm, 0.1, 2, 'Nozzle diameter (mm)');
  const remaining = Math.max(0, input.heightMm - input.firstLayerMm) / input.layerMm;
  // Remove only floating-point contact at an integer, not a manufacturing tolerance.
  const nearest = Math.round(remaining);
  const stable =
    Math.abs(remaining - nearest) <= 32 * Number.EPSILON * Math.max(1, remaining)
      ? nearest
      : remaining;
  const count = 1 + Math.ceil(stable);
  const stackMm = input.firstLayerMm + (count - 1) * input.layerMm;
  return {
    count,
    stackMm,
    excessMm: Math.max(0, stackMm - input.heightMm),
    nozzleRatio: input.layerMm / input.nozzleMm,
    profileReview:
      Math.max(input.layerMm, input.firstLayerMm) / input.nozzleMm >= 0.8 - 8 * Number.EPSILON,
  };
}

export function fitScenario(input: LabScenario['fit']) {
  bounded(input.cadHoleMm, 0.1, 1000, 'Coupon CAD hole diameter (mm)');
  bounded(input.measuredHoleMm, 0.1, 1000, 'Measured hole diameter (mm)');
  bounded(input.shaftMm, 0.1, 1000, 'Measured shaft diameter (mm)');
  bounded(input.clearanceMm, -5, 5, 'Desired diametral clearance (mm)');
  const biasMm = input.measuredHoleMm - input.cadHoleMm;
  const targetHoleMm = input.shaftMm + input.clearanceMm;
  const nextCadHoleMm = targetHoleMm - biasMm;
  if (targetHoleMm <= 0 || nextCadHoleMm <= 0 || nextCadHoleMm > 2000)
    throw new Error('These inputs do not produce a positive, supported hole diameter.');
  return { biasMm, targetHoleMm, nextCadHoleMm, radialClearanceMm: input.clearanceMm / 2 };
}

export function parseLabScenario(value: unknown): LabScenario {
  const data = value as Partial<LabScenario> | null;
  if (
    !data ||
    data.format !== 'pictures-to-cad-science' ||
    data.version !== 1 ||
    !['scale', 'layers', 'fit'].includes(data.active ?? '')
  )
    throw new Error('Choose a Pictures to CAD science scenario, version 1.');
  const numberFields = <T extends Record<string, number>>(source: unknown, defaults: T): T => {
    if (!source || typeof source !== 'object')
      throw new Error('The scenario is missing its input values.');
    return Object.fromEntries(
      Object.keys(defaults).map((key) => {
        const number = (source as Record<string, unknown>)[key];
        if (typeof number !== 'number' || !Number.isFinite(number))
          throw new Error(`Scenario field ${key} must be a finite number.`);
        return [key, number];
      }),
    ) as T;
  };
  const result: LabScenario = {
    format: 'pictures-to-cad-science',
    version: 1,
    active: data.active!,
    scale: numberFields(data.scale, LAB_DEFAULTS.scale),
    layers: numberFields(data.layers, LAB_DEFAULTS.layers),
    fit: numberFields(data.fit, LAB_DEFAULTS.fit),
  };
  scaleScenario(result.scale);
  layerScenario(result.layers);
  fitScenario(result.fit);
  return result;
}
