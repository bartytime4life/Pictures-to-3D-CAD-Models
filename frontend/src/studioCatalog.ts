/** One definition drives routing, titles, tabs, tool discovery and command navigation.
 * Keep this module free of component imports so it is usable in pure tests.
 */
export const STUDIO_CATALOG = [
  {
    id: 'start',
    label: 'Start',
    shortLabel: 'Start',
    name: 'Start',
    title: 'Start',
    description: 'Choose a making task, resume saved work and check local setup.',
    keywords: 'home getting started setup resume projects',
    category: 'Explore',
    requirement: 'No AI needed',
  },
  {
    id: 'designer',
    label: 'Shape designer',
    shortLabel: 'Shape',
    name: 'Flat part shape designer',
    title: 'Flat part shape designer',
    description: 'Combine common shapes and cutouts with automatic CAD preview.',
    keywords: 'draw rectangle circle slot triangle hexagon sketch design',
    category: 'Make',
    requirement: 'No AI needed',
  },
  {
    id: 'workbench',
    label: 'Flat part',
    shortLabel: 'Flat part',
    name: 'Flat-part workbench',
    title: 'Photo to profile workbench',
    description: 'Trace a measured photograph into an editable, constant-thickness solid.',
    keywords: 'photo cad model edit profile step stl dxf',
    category: 'Make',
    requirement: 'No AI needed',
  },
  {
    id: 'relief',
    label: 'Relief & Lithophane',
    shortLabel: 'Relief',
    name: 'Relief and lithophane studio',
    title: 'Relief & lithophane studio',
    description: 'Turn image intensity or a heightmap into printable depth.',
    keywords: 'terrain heightmap light depth',
    category: 'Make',
    requirement: 'Optional depth model',
  },
  {
    id: 'library',
    label: 'Photo library',
    shortLabel: 'Library',
    name: 'Photo library',
    title: 'Photo library',
    description: 'Organize, compare and choose source photographs for your projects.',
    keywords: 'images browse sources vision',
    category: 'Collect',
    requirement: 'Optional vision model',
  },
  {
    id: 'image',
    label: 'Image inspection',
    shortLabel: 'Image',
    name: 'Image inspection',
    title: 'Image inspection',
    description: 'Inspect contrast, exposure and selected regions; compare two source images.',
    keywords: 'histogram pixels brightness sobel difference before after image diagnostics',
    category: 'Explore',
    requirement: 'No AI needed',
  },
  {
    id: 'creative',
    label: 'Creative tools',
    shortLabel: 'Creative',
    name: 'Creative tools',
    title: 'Creative tools',
    description: 'Explore design directions, refine an idea and plan the making with local AI.',
    keywords: 'ideas brainstorm critique brief plan ollama ai',
    category: 'Explore',
    requirement: 'Local Ollama chat',
  },
  {
    id: 'knowledge',
    label: 'Knowledge',
    shortLabel: 'Knowledge',
    name: 'Knowledge base',
    title: 'Knowledge base',
    description: 'Find guides, troubleshoot a workflow and keep your own notes.',
    keywords: 'help documentation learn notes',
    category: 'Explore',
    requirement: 'No AI needed',
  },
  {
    id: 'science',
    label: 'Science lab',
    shortLabel: 'Science lab',
    name: 'Science lab',
    title: 'Science lab',
    description: 'Explore scale, print layers and fit with editable scenarios.',
    keywords: 'calculator sensitivity clearance experiment',
    category: 'Explore',
    requirement: 'No AI needed',
  },
] as const;

export type Studio = (typeof STUDIO_CATALOG)[number]['id'];
export type StudioDefinition = (typeof STUDIO_CATALOG)[number];

export function studioFromHash(hash: string): Studio {
  const target = hash.replace(/^#/, '').split('?')[0];
  return STUDIO_CATALOG.find((studio) => studio.id === target)?.id ?? 'start';
}

export function searchStudios(query: string, category = 'All'): StudioDefinition[] {
  const words = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  return STUDIO_CATALOG.filter(
    (studio) =>
      (category === 'All' || studio.category === category) &&
      words.every((word) =>
        `${studio.name} ${studio.description} ${studio.keywords} ${studio.requirement}`
          .toLowerCase()
          .includes(word),
      ),
  );
}
