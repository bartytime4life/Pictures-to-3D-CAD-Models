import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import type { TraceResult } from '../../frontend/src/types';

test('optional background removal keeps source colors and holes, and resets after retracing', async ({
  page,
}, testInfo) => {
  const jobs = new Set<string>();
  let traceRequests = 0;
  page.on('request', (request) => {
    if (new URL(request.url()).pathname === '/api/trace') traceRequests += 1;
  });
  page.on('response', async (response) => {
    if (response.url().endsWith('/api/build') && response.ok()) {
      const model = await response.json().catch(() => null);
      if (model?.id) jobs.add(model.id);
    }
  });
  try {
    const traced = page.waitForResponse(
      (response) => response.url().endsWith('/api/trace') && response.ok(),
    );
    await page.goto('/');
    const source = (await (await traced).json()) as TraceResult;
    await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
      timeout: 60_000,
    });
    const originalTraceRequests = traceRequests;
    await expect(page.locator('.source-canvas')).toHaveAttribute('data-background', 'original');
    await expect(page.getByRole('link', { name: 'Save transparent PNG' })).toHaveCount(0);
    await page.getByRole('button', { name: 'Remove background', exact: true }).click();
    const downloadLink = page.getByRole('link', { name: 'Save transparent PNG' });
    await expect(downloadLink).toBeVisible();
    await expect(page.locator('.source-canvas')).toHaveAttribute('data-background', 'removed');
    await expect(
      page.getByRole('button', { name: 'Background removed', exact: true }),
    ).toHaveAttribute('aria-pressed', 'true');
    const pixels = await page.evaluate(
      async ({ trace, cutoutUrl }) => {
        const load = async (url: string) => {
          const image = await createImageBitmap(await (await fetch(url)).blob());
          const canvas = document.createElement('canvas');
          canvas.width = image.width;
          canvas.height = image.height;
          const context = canvas.getContext('2d')!;
          context.drawImage(image, 0, 0);
          image.close();
          return {
            width: canvas.width,
            height: canvas.height,
            data: context.getImageData(0, 0, canvas.width, canvas.height).data,
          };
        };
        const original = await load(trace.image.data_url);
        const cutout = await load(cutoutUrl!);
        const inside = (x: number, y: number, loop: number[][]) => {
          let result = false;
          for (let i = 0, j = loop.length - 1; i < loop.length; j = i++) {
            const [ax, ay] = loop[i],
              [bx, by] = loop[j];
            if (ay > y !== by > y && x < ((bx - ax) * (y - ay)) / (by - ay) + ax) result = !result;
          }
          return result;
        };
        const nearEdge = (x: number, y: number, loop: number[][]) =>
          loop.some(([ax, ay], i) => {
            const [bx, by] = loop[(i + 1) % loop.length];
            const projection = Math.max(
              0,
              Math.min(
                1,
                ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) /
                  ((bx - ax) ** 2 + (by - ay) ** 2 || 1),
              ),
            );
            return Math.hypot(x - ax - projection * (bx - ax), y - ay - projection * (by - ay)) < 2;
          });
        const result = {
          width: cutout.width,
          height: cutout.height,
          material: 0,
          outside: 0,
          holes: 0,
          errors: 0,
        };
        const loops = [trace.profile.outer, ...trace.profile.holes];
        const stride = Math.max(1, Math.floor(Math.min(cutout.width, cutout.height) / 80));
        for (let y = 0; y < cutout.height; y += stride) {
          for (let x = 0; x < cutout.width; x += stride) {
            if (loops.some((loop) => nearEdge(x + 0.5, y + 0.5, loop))) continue;
            const offset = (y * cutout.width + x) * 4;
            const inHole = trace.profile.holes.some((loop) => inside(x + 0.5, y + 0.5, loop));
            const inOuter = inside(x + 0.5, y + 0.5, trace.profile.outer);
            if (!inOuter || inHole) {
              if (inHole) result.holes += 1;
              else result.outside += 1;
              if (cutout.data[offset + 3] !== 0) result.errors += 1;
            } else {
              result.material += 1;
              if (
                [0, 1, 2, 3].some(
                  (channel) => cutout.data[offset + channel] !== original.data[offset + channel],
                )
              )
                result.errors += 1;
            }
          }
        }
        return result;
      },
      { trace: source, cutoutUrl: await downloadLink.getAttribute('href') },
    );
    expect(pixels.width).toBe(source.image.width);
    expect(pixels.height).toBe(source.image.height);
    expect(pixels.material).toBeGreaterThan(20);
    expect(pixels.outside).toBeGreaterThan(20);
    expect(pixels.holes).toBeGreaterThan(5);
    expect(pixels.errors).toBe(0);
    await page.screenshot({ path: testInfo.outputPath('background-removed.png'), fullPage: true });
    expect(traceRequests).toBe(originalTraceRequests);
    await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();

    await page.getByRole('button', { name: 'Original', exact: true }).click();
    await expect(page.locator('.source-canvas')).toHaveAttribute('data-background', 'original');
    await expect(page.getByRole('button', { name: 'Original', exact: true })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await page.getByRole('button', { name: 'Background removed', exact: true }).click();
    const downloadEvent = page.waitForEvent('download');
    await downloadLink.click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toMatch(/-transparent\.png$/);
    const output = testInfo.outputPath(download.suggestedFilename());
    await download.saveAs(output);
    const png = await readFile(output);
    expect(png.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a');
    expect(png.readUInt32BE(16)).toBe(source.image.width);
    expect(png.readUInt32BE(20)).toBe(source.image.height);
    const newTrace = page.waitForResponse(
      (response) => response.url().endsWith('/api/trace') && response.ok(),
    );
    await page.getByLabel('Outline detail', { exact: true }).selectOption('fine');
    await newTrace;
    await expect(
      page.getByRole('button', { name: 'Remove background', exact: true }),
    ).toBeEnabled();
    await expect(downloadLink).toHaveCount(0);
    await expect(page.locator('.source-canvas')).toHaveAttribute('data-background', 'original');
    await expect(page.getByRole('button', { name: 'Original', exact: true })).toHaveCount(0);
  } finally {
    for (const id of jobs) await page.request.delete(`/api/models/${id}`);
  }
});
