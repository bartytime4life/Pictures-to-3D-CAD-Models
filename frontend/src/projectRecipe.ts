import { saveStudioJson } from './studioFiles';
import type { Profile, ProjectRecipe } from './types';

export function downloadProjectRecipe(recipe: ProjectRecipe) {
  const name = recipe.name.replace(/[^a-zA-Z0-9_-]+/g, '-').slice(0, 60) || 'part';
  saveStudioJson(recipe, `${name}.cad-project.json`);
}

export function profileBounds(profile: Profile) {
  const xs = profile.outer.map(([x]) => x);
  const ys = profile.outer.map(([, y]) => y);
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  return { x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y };
}
