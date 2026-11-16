// Passing a photo from the library to another studio. The studios are separate pages
// behind one hash router and each mounts fresh, so the file waits here for the moment
// the target studio mounts and takes it. It is held in memory only and taken once.
export type HandoffTarget = 'workbench' | 'relief';

let pending: { target: HandoffTarget; file: File } | null = null;

export function handOff(target: HandoffTarget, file: File) {
  pending = { target, file };
  window.location.hash = target === 'relief' ? '#relief' : '#workbench';
}

export function takeHandoff(target: HandoffTarget): File | null {
  if (pending?.target !== target) return null;
  const { file } = pending;
  pending = null;
  return file;
}
