/** Serialize complete async operations for one key while other keys continue independently. */
export class KeyedTaskQueue<Key> {
  private readonly tails = new Map<Key, Promise<void>>();

  get pendingKeys() {
    return this.tails.size;
  }

  run<Result>(key: Key, task: () => Promise<Result> | Result): Promise<Result> {
    const previous = this.tails.get(key) ?? Promise.resolve();
    const result = previous.then(task);
    // A rejected operation must not poison the next operation for this key.
    const settled = result.then(
      () => {},
      () => {},
    );
    this.tails.set(key, settled);
    return result.finally(() => {
      // An older completion must not delete the tail of a newer queued operation.
      if (this.tails.get(key) === settled) this.tails.delete(key);
    });
  }
}
