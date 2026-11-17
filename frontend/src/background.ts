import type { TraceResult } from './types';

/** Make a separate image from the same pixel frame as the reviewed outline.
 * The source file and the trace are never changed. Reference-sheet traces already
 * carry their corrected working image, so no second orientation or scaling occurs.
 */
export async function createBackgroundCutout(
  trace: TraceResult,
  signal?: AbortSignal,
): Promise<Blob> {
  const { width, height, data_url: dataUrl } = trace.image;
  if (
    !Number.isSafeInteger(width) ||
    !Number.isSafeInteger(height) ||
    width < 1 ||
    height < 1 ||
    width * height > 70_000_000 ||
    !dataUrl.startsWith('data:image/png;base64,')
  )
    throw new Error('Choose and trace a photo before removing its background.');
  const loops = [trace.profile.outer, ...trace.profile.holes];
  if (
    loops.some(
      (loop) =>
        loop.length < 3 || loop.some(([x, y]) => !Number.isFinite(x) || !Number.isFinite(y)),
    )
  )
    throw new Error('Review the outline before removing the background.');
  signal?.throwIfAborted();
  const image = new Image();
  await new Promise<void>((resolve, reject) => {
    const cleanup = () => {
      image.onload = null;
      image.onerror = null;
      signal?.removeEventListener('abort', abort);
    };
    const abort = () => {
      cleanup();
      image.src = '';
      reject(new DOMException('Background removal cancelled.', 'AbortError'));
    };
    image.onload = () => {
      cleanup();
      resolve();
    };
    image.onerror = () => {
      cleanup();
      reject(new Error('The working photo could not be read. Trace the photo again.'));
    };
    signal?.addEventListener('abort', abort, { once: true });
    image.src = dataUrl;
  });
  signal?.throwIfAborted();
  if (image.naturalWidth !== width || image.naturalHeight !== height)
    throw new Error('The photo and outline dimensions do not match. Trace the photo again.');
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  try {
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Background removal is unavailable in this browser.');
    context.beginPath();
    for (const loop of loops) {
      context.moveTo(loop[0][0], loop[0][1]);
      for (const [x, y] of loop.slice(1)) context.lineTo(x, y);
      context.closePath();
    }
    // Even-odd clipping preserves all through holes regardless of winding direction.
    context.clip('evenodd');
    context.drawImage(image, 0, 0);
    const blob = await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob(
        (result) =>
          result
            ? resolve(result)
            : reject(new Error('The transparent PNG could not be created. Try again.')),
        'image/png',
      ),
    );
    signal?.throwIfAborted();
    return blob;
  } finally {
    // Release the potentially large backing store after the asynchronous PNG encoder.
    canvas.width = 0;
    canvas.height = 0;
  }
}
