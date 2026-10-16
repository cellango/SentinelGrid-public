export interface AIConfidenceDescriptor {
  label: string;
  tone: 'high' | 'medium' | 'low' | 'review';
}

function parseConfidenceValue(value?: number | string | null): number | null {
  if (value == null) {
    return null;
  }

  const raw =
    typeof value === 'number'
      ? value
      : Number.parseFloat(String(value).replace('%', '').trim());

  if (!Number.isFinite(raw)) {
    return null;
  }

  return raw <= 1 ? raw * 100 : raw;
}

export function describeAIConfidence(
  value?: number | string | null
): AIConfidenceDescriptor | null {
  const parsed = parseConfidenceValue(value);
  if (parsed == null) {
    return null;
  }

  if (parsed >= 90) {
    return { label: 'High confidence', tone: 'high' };
  }
  if (parsed >= 70) {
    return { label: 'Medium confidence', tone: 'medium' };
  }
  if (parsed >= 50) {
    return { label: 'Low confidence', tone: 'low' };
  }
  return { label: 'Needs review', tone: 'review' };
}

export function inferAIProcessingLabel(input: {
  localProcessing?: boolean;
  processingHint?: string | null;
  provider?: string | null;
  modelName?: string | null;
  sourceLabel?: string | null;
}): string | null {
  if (input.localProcessing === true) {
    return 'Processed locally';
  }

  if (input.localProcessing === false) {
    return null;
  }

  const haystack = [
    input.processingHint,
    input.provider,
    input.modelName,
    input.sourceLabel,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (!haystack) {
    return null;
  }

  if (
    haystack.includes('self-hosted') ||
    haystack.includes('self hosted') ||
    haystack.includes('self_hosted') ||
    haystack.includes('on-prem') ||
    haystack.includes('on prem')
  ) {
    return 'Self-hosted inference';
  }

  if (
    haystack.includes('model gateway') ||
    haystack.includes('model_gateway') ||
    haystack.includes('local') ||
    haystack.includes('internal') ||
    haystack.includes('llama') ||
    haystack.includes('ollama') ||
    haystack.includes('vllm') ||
    haystack.includes('secgpt') ||
    haystack.includes('lily') ||
    haystack.includes('sentinelgrid-ai')
  ) {
    return 'Processed locally';
  }

  return null;
}
