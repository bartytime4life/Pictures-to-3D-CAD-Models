import { localAIRequest } from './creative.ts';
import type { CreativeTool } from './creative.ts';
import type { AssistantStatus } from './types.ts';

type Request = <T>(url: string, init?: RequestInit) => Promise<T>;

function failure(reason: unknown, fallback: string) {
  return reason instanceof Error && !(reason instanceof TypeError) && reason.name !== 'AbortError'
    ? reason.message
    : fallback;
}

/** Tool discovery and Ollama readiness are independent: either can still be useful alone. */
export async function readCreativeConnection(
  signal: AbortSignal,
  request: Request = localAIRequest,
) {
  const [catalog, connection] = await Promise.allSettled([
    request<{ tools: CreativeTool[] }>('/api/creative/tools', { signal }),
    request<AssistantStatus>('/api/assistant/status', { signal }),
  ]);
  return {
    tools: catalog.status === 'fulfilled' ? catalog.value.tools : null,
    toolError:
      catalog.status === 'rejected'
        ? failure(catalog.reason, 'Could not load the creative tools. Refresh to try again.')
        : '',
    status: connection.status === 'fulfilled' ? connection.value : null,
    connectionError:
      connection.status === 'rejected'
        ? failure(
            connection.reason,
            'Could not check local AI. Start the CAD service and Ollama, then refresh.',
          )
        : '',
  };
}
