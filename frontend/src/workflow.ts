export type WorkflowAction = 'photo' | 'width' | 'thickness' | 'design' | 'build' | 'export';
export type WorkflowStage = 'photo' | 'trace' | 'scale' | 'export';

/** Readiness describes editable inputs and the current digital build, not physical acceptance. */
export function workflowState(input: {
  hasTrace: boolean;
  hasModel: boolean;
  current: boolean;
  validWidth: boolean;
  validThickness: boolean;
  designIssue: string;
  busy: string | null;
}): {
  stage: WorkflowStage | null;
  title: string;
  detail: string;
  footer: string;
  action: WorkflowAction | null;
  actionLabel: string;
} {
  if (input.busy)
    return {
      stage: null,
      title: 'Working on your model',
      detail: input.busy,
      footer: 'Processing',
      action: null,
      actionLabel: '',
    };
  if (!input.hasTrace)
    return {
      stage: 'photo',
      title: 'Start with your part',
      detail: 'Choose a photo of one flat part, or open a saved project.',
      footer: 'Choose a source',
      action: 'photo',
      actionLabel: 'Choose a source',
    };
  if (!input.validWidth)
    return {
      stage: 'scale',
      title: 'Set your measured width',
      detail: 'Enter the full outside width, or use a measured feature to set scale.',
      footer: 'Awaiting measurements',
      action: 'width',
      actionLabel: 'Enter width',
    };
  if (!input.validThickness)
    return {
      stage: 'scale',
      title: 'Add the measured thickness',
      detail: 'Measure thickness separately. The photograph supplies the flat outline.',
      footer: 'Awaiting measurements',
      action: 'thickness',
      actionLabel: 'Enter thickness',
    };
  if (input.designIssue)
    return {
      stage: 'scale',
      title: 'Review your design settings',
      detail: input.designIssue,
      footer: 'Review settings',
      action: 'design',
      actionLabel: 'Fix design settings',
    };
  if (input.current)
    return {
      stage: 'export',
      title: 'Ready to review your model',
      detail:
        'The model matches your current settings. Inspect its dimensions, then choose an export.',
      footer: 'Solid ready',
      action: 'export',
      actionLabel: 'Choose an export',
    };
  return input.hasModel
    ? {
        stage: 'scale',
        title: 'Bring your preview up to date',
        detail:
          'Your settings changed. Update the model before reviewing or downloading its geometry.',
        footer: 'Rebuild needed',
        action: 'build',
        actionLabel: 'Update preview',
      }
    : {
        stage: 'scale',
        title: 'Create your CAD preview',
        detail: 'Your measurements and settings are ready. Build the solid to inspect the result.',
        footer: 'Ready to build',
        action: 'build',
        actionLabel: 'Create preview',
      };
}
