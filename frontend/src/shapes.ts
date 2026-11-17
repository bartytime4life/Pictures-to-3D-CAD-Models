export type ShapeKind =
  'rectangle' | 'rounded_rectangle' | 'circle' | 'slot' | 'triangle' | 'hexagon';
export type DesignShape = {
  id: string;
  kind: ShapeKind;
  operation: 'add' | 'cut';
  x_mm: number;
  y_mm: number;
  width_mm: number;
  height_mm: number;
  corner_mm: number;
  rotation_deg: number;
};
export type ShapeDraft = { name: string; thickness_mm: number; shapes: DesignShape[] };
export const SHAPE_LABELS: Record<ShapeKind, string> = {
  rectangle: 'Rectangle',
  rounded_rectangle: 'Rounded rectangle',
  circle: 'Circle',
  slot: 'Slot',
  triangle: 'Triangle',
  hexagon: 'Hexagon',
};
export function newShape(kind: ShapeKind, operation: 'add' | 'cut' = 'add'): DesignShape {
  return {
    id: crypto.randomUUID(),
    kind,
    operation,
    x_mm: 0,
    y_mm: 0,
    width_mm: operation === 'cut' ? 12 : 30,
    height_mm: operation === 'cut' ? 12 : 24,
    corner_mm: 3,
    rotation_deg: 0,
  };
}
export function shapeTemplate(template: string): ShapeDraft {
  const base = { ...newShape('rounded_rectangle'), width_mm: 80, height_mm: 50, corner_mm: 6 };
  if (template === 'washer')
    return {
      name: 'Washer',
      thickness_mm: 3,
      shapes: [
        { ...newShape('circle'), width_mm: 40, height_mm: 40 },
        { ...newShape('circle', 'cut'), width_mm: 14, height_mm: 14 },
      ],
    };
  if (template === 'tab')
    return {
      name: 'Slotted tab',
      thickness_mm: 4,
      shapes: [
        { ...newShape('slot'), width_mm: 60, height_mm: 24 },
        { ...newShape('slot', 'cut'), width_mm: 24, height_mm: 8 },
      ],
    };
  if (template === 'blank') return { name: 'Shape design', thickness_mm: 4, shapes: [base] };
  return {
    name: 'Mounting plate',
    thickness_mm: 4,
    shapes: [
      base,
      { ...newShape('circle', 'cut'), x_mm: -28, width_mm: 8, height_mm: 8 },
      { ...newShape('circle', 'cut'), x_mm: 28, width_mm: 8, height_mm: 8 },
    ],
  };
}

export function shapeDraftIssue(draft: ShapeDraft): string {
  if (!draft.name.trim() || draft.name.length > 100 || /[\u0000-\u001f\u007f]/.test(draft.name))
    return 'Enter a project name without control characters (up to 100 characters).';
  if (!Number.isFinite(draft.thickness_mm) || draft.thickness_mm < 0.1 || draft.thickness_mm > 500)
    return 'Thickness must be between 0.1 and 500 mm.';
  if (!Array.isArray(draft.shapes) || !draft.shapes.length || draft.shapes.length > 16)
    return 'Use between 1 and 16 shapes.';
  if (!draft.shapes.some((shape) => shape.operation === 'add'))
    return 'Add at least one material shape.';
  const ids = new Set<string>();
  for (const shape of draft.shapes) {
    if (!Object.hasOwn(SHAPE_LABELS, shape.kind) || !['add', 'cut'].includes(shape.operation))
      return 'Choose a supported shape and operation.';
    if (typeof shape.id !== 'string' || !shape.id || shape.id.length > 60 || ids.has(shape.id))
      return 'Each shape needs a unique ID.';
    ids.add(shape.id);
    if (
      ![shape.width_mm, shape.height_mm].every((n) => Number.isFinite(n) && n >= 0.5 && n <= 1000)
    )
      return 'Shape sizes must be between 0.5 and 1000 mm.';
    if (![shape.x_mm, shape.y_mm].every((n) => Number.isFinite(n) && Math.abs(n) <= 1000))
      return 'Shape positions must be between −1000 and 1000 mm.';
    if (!Number.isFinite(shape.rotation_deg) || Math.abs(shape.rotation_deg) > 180)
      return 'Rotation must be between −180° and 180°.';
    if (!Number.isFinite(shape.corner_mm) || shape.corner_mm < 0 || shape.corner_mm > 500)
      return 'Enter a valid corner radius.';
    if (
      shape.kind === 'rounded_rectangle' &&
      shape.corner_mm > Math.min(shape.width_mm, shape.height_mm) / 2
    )
      return 'Corner radius must be no more than half the smaller side.';
  }
  return '';
}

export function parseShapeDraft(value: unknown): ShapeDraft {
  const data = value as { format?: string; version?: number; design?: ShapeDraft } | null;
  if (
    !data ||
    data.format !== 'pictures-to-cad-shapes' ||
    data.version !== 1 ||
    !data.design ||
    typeof data.design.name !== 'string' ||
    !Array.isArray(data.design.shapes) ||
    data.design.shapes.some((shape) => !shape || typeof shape !== 'object')
  )
    throw new Error('Choose a saved Pictures to CAD shape design.');
  // Only copy known fields; importing a draft cannot add backend instructions.
  const draft: ShapeDraft = {
    name: data.design.name,
    thickness_mm: data.design.thickness_mm,
    shapes: data.design.shapes.map((shape) => ({
      id: shape.id,
      kind: shape.kind,
      operation: shape.operation,
      x_mm: shape.x_mm,
      y_mm: shape.y_mm,
      width_mm: shape.width_mm,
      height_mm: shape.height_mm,
      corner_mm: shape.corner_mm,
      rotation_deg: shape.rotation_deg,
    })),
  };
  const issue = shapeDraftIssue(draft);
  if (issue) throw new Error(issue);
  return draft;
}

export function shapePath(context: CanvasRenderingContext2D, shape: DesignShape) {
  const w = shape.width_mm,
    h = shape.kind === 'circle' ? w : shape.height_mm;
  context.beginPath();
  if (shape.kind === 'circle') context.arc(0, 0, w / 2, 0, Math.PI * 2);
  else if (shape.kind === 'rectangle') context.rect(-w / 2, -h / 2, w, h);
  else if (shape.kind === 'rounded_rectangle' || shape.kind === 'slot')
    context.roundRect(
      -w / 2,
      -h / 2,
      w,
      h,
      Math.max(0, Math.min(w / 2, h / 2, shape.kind === 'slot' ? Infinity : shape.corner_mm)),
    );
  else {
    const points =
      shape.kind === 'triangle'
        ? [
            [-w / 2, h / 2],
            [0, -h / 2],
            [w / 2, h / 2],
          ]
        : [
            [-w / 4, -h / 2],
            [w / 4, -h / 2],
            [w / 2, 0],
            [w / 4, h / 2],
            [-w / 4, h / 2],
            [-w / 2, 0],
          ];
    points.forEach(([x, y], index) => (index ? context.lineTo(x, y) : context.moveTo(x, y)));
    context.closePath();
  }
}
