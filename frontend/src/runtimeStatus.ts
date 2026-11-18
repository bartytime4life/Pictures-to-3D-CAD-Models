export type RuntimeCheck = {
  id: string;
  label: string;
  status: 'ready' | 'missing' | 'limited';
  required: boolean;
  detail: string;
  action?: { label: string; command: string };
};

export type RuntimeStatus = { ready: boolean; checks: RuntimeCheck[] };

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function text(value: unknown, maximum: number): value is string {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= maximum;
}

/** Validate the read-only setup report before displaying a readiness claim or setup action. */
export function parseRuntimeStatus(value: unknown): RuntimeStatus {
  const invalid = () => new Error('The setup response was incomplete.');
  if (
    !record(value) ||
    typeof value.ready !== 'boolean' ||
    !Array.isArray(value.checks) ||
    value.checks.length === 0 ||
    value.checks.length > 32
  )
    throw invalid();
  const identifiers = new Set<string>();
  const checks = value.checks.map((item): RuntimeCheck => {
    if (
      !record(item) ||
      !text(item.id, 100) ||
      identifiers.has(item.id) ||
      !text(item.label, 200) ||
      typeof item.status !== 'string' ||
      !['ready', 'missing', 'limited'].includes(item.status) ||
      typeof item.required !== 'boolean' ||
      !text(item.detail, 4000)
    )
      throw invalid();
    identifiers.add(item.id);
    const check: RuntimeCheck = {
      id: item.id,
      label: item.label,
      status: item.status as RuntimeCheck['status'],
      required: item.required,
      detail: item.detail,
    };
    if (item.action !== undefined) {
      if (!record(item.action) || !text(item.action.label, 200) || !text(item.action.command, 2000))
        throw invalid();
      check.action = { label: item.action.label, command: item.action.command };
    }
    return check;
  });
  const core = checks.filter((check) => check.required);
  if (!core.length || value.ready !== core.every((check) => check.status === 'ready'))
    throw invalid();
  return { ready: value.ready, checks };
}
