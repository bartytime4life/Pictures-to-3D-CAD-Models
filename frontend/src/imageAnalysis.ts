/** Image diagnostics adapted from Intelligent-DVR-Tool's image-science method.
 * Source and mathematical limits: docs/image-inspection.md. No network or AI.
 */
export type Raster = { width: number; height: number; data: Uint8ClampedArray };
export type Region = { x: number; y: number; width: number; height: number };
export const FULL_IMAGE: Region = { x: 0, y: 0, width: 1, height: 1 };
export const SAMPLE_SIDE = 720;
export const SOBEL_MAXIMUM = 255 * Math.sqrt(20);
export const IMAGE_METHOD = 'picad-srgb-white-sobel-v1';

export function regionBounds(region: Region, width: number, height: number) {
  if (![width, height].every((n) => Number.isInteger(n) && n >= 1 && n <= SAMPLE_SIDE))
    throw new Error('Expected an image sampled to at most 720 pixels per side.');
  if (
    !Object.values(region).every(Number.isFinite) ||
    region.x < 0 ||
    region.y < 0 ||
    region.width <= 0 ||
    region.height <= 0 ||
    region.x + region.width > 1 + 1e-10 ||
    region.y + region.height > 1 + 1e-10
  )
    throw new Error('Choose a nonempty region inside the image.');
  const left = Math.min(width - 1, Math.floor(region.x * width));
  const top = Math.min(height - 1, Math.floor(region.y * height));
  return {
    left,
    top,
    right: Math.min(width, Math.ceil((region.x + region.width) * width)),
    bottom: Math.min(height, Math.ceil((region.y + region.height) * height)),
  };
}

function check(image: Raster) {
  regionBounds(FULL_IMAGE, image.width, image.height);
  if (
    !(image.data instanceof Uint8ClampedArray) ||
    image.data.length !== image.width * image.height * 4
  )
    throw new Error('Expected bounded RGBA pixels.');
}

function luma(data: Uint8ClampedArray, offset: number) {
  const alpha = data[offset + 3] / 255;
  // White matches this app's flat-part photo backing. The DVR uses black.
  return Math.round(
    (0.2126 * data[offset] + 0.7152 * data[offset + 1] + 0.0722 * data[offset + 2]) * alpha +
      255 * (1 - alpha),
  );
}

export function analyzeImage(image: Raster, region: Region = FULL_IMAGE) {
  check(image);
  const bounds = regionBounds(region, image.width, image.height);
  const width = bounds.right - bounds.left,
    height = bounds.bottom - bounds.top;
  const shades = new Uint8Array(width * height);
  const histogram = new Array<number>(16).fill(0),
    levels = new Array<number>(256).fill(0);
  let sum = 0,
    shadows = 0,
    highlights = 0;
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++) {
      const value = luma(image.data, ((y + bounds.top) * image.width + x + bounds.left) * 4);
      shades[y * width + x] = value;
      histogram[value >> 4]++;
      levels[value]++;
      sum += value;
      if (value <= 15) shadows++;
      if (value >= 240) highlights++;
    }
  const pixels = width * height;
  const percentile = (fraction: number) => {
    const target = Math.max(1, Math.ceil(pixels * fraction));
    let seen = 0;
    for (let value = 0; value < 256; value++) {
      seen += levels[value];
      if (seen >= target) return value;
    }
    return 255;
  };
  let strength = 0;
  for (let y = 1; y < height - 1; y++)
    for (let x = 1; x < width - 1; x++) {
      const k = y * width + x;
      const gx =
        -shades[k - width - 1] +
        shades[k - width + 1] -
        2 * shades[k - 1] +
        2 * shades[k + 1] -
        shades[k + width - 1] +
        shades[k + width + 1];
      const gy =
        -shades[k - width - 1] -
        2 * shades[k - width] -
        shades[k - width + 1] +
        shades[k + width - 1] +
        2 * shades[k + width] +
        shades[k + width + 1];
      strength += Math.sqrt((gx * gx + gy * gy) / (20 * 255 * 255));
    }
  const edgeSamples = Math.max(0, width - 2) * Math.max(0, height - 2);
  return {
    method: IMAGE_METHOD,
    bounds,
    width,
    height,
    pixels,
    mean: sum / pixels,
    low: percentile(0.05),
    high: percentile(0.95),
    shadows: (shadows / pixels) * 100,
    highlights: (highlights / pixels) * 100,
    edgeStrength: edgeSamples ? (strength / edgeSamples) * 100 : null,
    edgeSamples,
    histogram,
  };
}

export function compareImages(a: Raster, b: Raster, region: Region = FULL_IMAGE, threshold = 24) {
  check(a);
  check(b);
  if (!Number.isFinite(threshold) || threshold < 0 || threshold > 255)
    throw new Error('Invalid difference threshold.');
  if (a.width !== b.width || a.height !== b.height) return null;
  const bounds = regionBounds(region, a.width, a.height);
  let absolute = 0,
    changed = 0,
    pixels = 0;
  for (let y = bounds.top; y < bounds.bottom; y++)
    for (let x = bounds.left; x < bounds.right; x++) {
      const k = (y * a.width + x) * 4;
      const difference = Math.abs(luma(a.data, k) - luma(b.data, k));
      absolute += difference;
      pixels++;
      if (difference > 0 && difference >= threshold) changed++;
    }
  return {
    pixels,
    threshold,
    meanAbsoluteDifference: absolute / pixels,
    changedPercent: (changed / pixels) * 100,
  };
}
