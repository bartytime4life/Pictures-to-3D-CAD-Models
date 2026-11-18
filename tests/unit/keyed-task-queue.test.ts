import { test } from 'node:test';
import assert from 'node:assert/strict';
import { KeyedTaskQueue } from '../../frontend/src/keyedTaskQueue.ts';

function gate() {
  let release!: () => void;
  const promise = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { promise, release };
}

test('a save delayed before storage opens cannot be overtaken by a later save of the same project', async () => {
  const queue = new KeyedTaskQueue<number>();
  const opening = gate();
  const events: string[] = [];
  let stored = 'Original';
  const first = queue.run(7, async () => {
    events.push('A opening');
    await opening.promise;
    stored = 'A';
    events.push('A committed');
    return stored;
  });
  await Promise.resolve();
  const second = queue.run(7, () => {
    events.push('B opening');
    stored = 'B';
    events.push('B committed');
    return stored;
  });
  await Promise.resolve();
  assert.deepEqual(events, ['A opening']);
  assert.equal(stored, 'Original');
  opening.release();
  assert.deepEqual(await Promise.all([first, second]), ['A', 'B']);
  assert.deepEqual(events, ['A opening', 'A committed', 'B opening', 'B committed']);
  assert.equal(stored, 'B');
  assert.equal(queue.pendingKeys, 0);
});

test('failed saves reject their caller while the next save continues and the key is released', async () => {
  const queue = new KeyedTaskQueue<number>();
  const opening = gate();
  const first = queue.run(7, async () => {
    await opening.promise;
    throw new Error('Storage unavailable.');
  });
  const rejected = assert.rejects(first, /Storage unavailable/);
  const second = queue.run(7, () => 'Recovered save.');
  opening.release();
  await rejected;
  assert.equal(await second, 'Recovered save.');
  assert.equal(queue.pendingKeys, 0);
  await assert.rejects(
    queue.run(7, () => {
      throw new Error('Synchronous failure.');
    }),
    /Synchronous failure/,
  );
  assert.equal(await queue.run(7, () => 'Still usable.'), 'Still usable.');
  assert.equal(queue.pendingKeys, 0);
});

test('different projects can save independently while one storage open is held', async () => {
  const queue = new KeyedTaskQueue<number>();
  const opening = gate();
  let firstCommitted = false;
  const first = queue.run(7, async () => {
    await opening.promise;
    firstCommitted = true;
  });
  assert.equal(await queue.run(8, () => 'Other project committed.'), 'Other project committed.');
  assert.equal(firstCommitted, false);
  assert.equal(queue.pendingKeys, 1);
  opening.release();
  await first;
  assert.equal(queue.pendingKeys, 0);
});

test('an older completion cannot remove the tail that keeps subsequent saves in order', async () => {
  const queue = new KeyedTaskQueue<number>();
  const writing = gate();
  const first = queue.run(7, () => 'A');
  const second = queue.run(7, async () => {
    await writing.promise;
    return 'B';
  });
  await first;
  assert.equal(queue.pendingKeys, 1);
  let thirdStarted = false;
  const third = queue.run(7, () => {
    thirdStarted = true;
    return 'C';
  });
  await Promise.resolve();
  assert.equal(thirdStarted, false);
  writing.release();
  assert.deepEqual(await Promise.all([second, third]), ['B', 'C']);
  assert.equal(queue.pendingKeys, 0);
});
