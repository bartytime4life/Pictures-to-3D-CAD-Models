import { test, expect } from '@playwright/test';

test('lifting a second finger preserves the primary shape drag and its single undo step', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto('/#designer');
  await page.getByRole('button', { name: 'Blank plate', exact: true }).click();
  const centerX = page.getByRole('spinbutton', { name: 'Center X (mm)', exact: true });
  await expect(centerX).toHaveValue('0');
  const canvas = page.getByRole('img', { name: /^2D shape design\./ });
  await canvas.scrollIntoViewIfNeeded();
  const bounds = await canvas.boundingBox();
  expect(bounds).not.toBeNull();
  const x = bounds!.x + bounds!.width / 2;
  const y = bounds!.y + bounds!.height / 2;
  const cdp = await page.context().newCDPSession(page);
  let touching = false;
  try {
    await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 2 });
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchStart',
      touchPoints: [{ id: 1, x, y }],
    });
    touching = true;
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [{ id: 1, x: x + 20, y }],
    });
    await expect.poll(async () => Number(await centerX.inputValue())).toBeGreaterThan(0);
    const firstMove = Number(await centerX.inputValue());

    // Chromium's active contact list adds/removes secondary fingers on touchMove.
    // https://chromium.googlesource.com/chromium/src/+/refs/heads/main/content/browser/devtools/protocol/input_handler.cc
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [
        { id: 1, x: x + 20, y },
        { id: 2, x: x + 70, y: y + 20 },
      ],
    });
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [{ id: 1, x: x + 20, y }],
    });
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [{ id: 1, x: x + 45, y }],
    });
    await expect.poll(async () => Number(await centerX.inputValue())).toBeGreaterThan(firstMove);
    const finalMove = await centerX.inputValue();
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    touching = false;

    await page.getByRole('button', { name: 'Undo shape edit', exact: true }).click();
    await expect(centerX).toHaveValue('0');
    await page.getByRole('button', { name: 'Redo shape edit', exact: true }).click();
    await expect(centerX).toHaveValue(finalMove);
  } finally {
    if (touching)
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] });
    await cdp.detach();
  }
});
