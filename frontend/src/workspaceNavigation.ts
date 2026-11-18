/** Explicit entry actions are separate from ordinary navigation, which preserves drafts. */
export type WorkbenchEntry = 'photo' | 'projects' | 'sample';
export function workbenchEntry(hash: string): WorkbenchEntry | null {
  const [route, query = ''] = hash.replace(/^#/, '').split('?');
  if (route !== 'workbench') return null;
  const entry = new URLSearchParams(query).get('open');
  return entry === 'photo' || entry === 'projects' || entry === 'sample' ? entry : null;
}
