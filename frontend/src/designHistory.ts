import type { DesignSettings } from './types';

export const DESIGN_HISTORY_LIMIT = 30;

/** Settings only: an old model's export files may already have been released. */
export type DesignHistory = {
  past: DesignSettings[];
  future: DesignSettings[];
};

export function createDesignHistory(): DesignHistory {
  return { past: [], future: [] };
}

export function sameDesign(left: DesignSettings, right: DesignSettings): boolean {
  const keys = Object.keys(left) as (keyof DesignSettings)[];
  return keys.length === Object.keys(right).length && keys.every((key) => left[key] === right[key]);
}

export function recordDesignChange(
  history: DesignHistory,
  previous: DesignSettings,
  next: DesignSettings,
): DesignHistory {
  if (sameDesign(previous, next)) return history;
  return {
    past: [...history.past, { ...previous }].slice(-DESIGN_HISTORY_LIMIT),
    future: [],
  };
}

export function undoDesignChange(history: DesignHistory, current: DesignSettings) {
  const previous = history.past.at(-1);
  if (!previous) return null;
  return {
    design: { ...previous },
    history: {
      past: history.past.slice(0, -1),
      future: [{ ...current }, ...history.future].slice(0, DESIGN_HISTORY_LIMIT),
    },
  };
}

export function redoDesignChange(history: DesignHistory, current: DesignSettings) {
  const next = history.future[0];
  if (!next) return null;
  return {
    design: { ...next },
    history: {
      past: [...history.past, { ...current }].slice(-DESIGN_HISTORY_LIMIT),
      future: history.future.slice(1),
    },
  };
}
