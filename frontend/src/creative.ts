export type CreativeTool = {
  id: string;
  name: string;
  description: string;
  starter: string;
  requires: string[];
  output: string;
};
export type CreativeInput = { model: string; tool: string; brief: string; constraints: string };
export type CreativeReply = {
  format: 'creative-notes-v1';
  tool: string;
  model: string;
  elapsed_seconds: number;
  warnings: string[];
  notes: {
    title: string;
    summary: string;
    sections: { title: string; body: string }[];
    next_steps: string[];
  };
};

export async function localAIRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : 'The local AI service could not respond. Try again.',
    );
  return data as T;
}

export function notesExport(input: CreativeInput, result: CreativeReply) {
  return { format: 'pictures-to-cad-creative-notes', version: 1, input, result };
}
