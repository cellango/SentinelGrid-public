import type { Incident } from '@/lib/api/incidents';
import type { Alert } from '@/lib/api/siem';
import { RESPONSE_PACKS, matchResponsePacksForAlert, matchResponsePacksForIncident } from '@/lib/playbooks/responsePacks';

function buildAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    id: 'alert-1',
    tenant_id: 'tenant-demo',
    severity: 'high',
    status: 'open',
    title: 'AI finding',
    source: 'sentinelgrid_ai_shield',
    created_at: '2026-03-26T00:00:00Z',
    updated_at: '2026-03-26T00:00:00Z',
    story_domains: ['ai', 'application', 'security'],
    raw_payload: {
      category: 'ai',
      ai: {
        app_id: 'copilot-finance',
        provider: 'openai',
        model: 'gpt-4.1',
      },
      ...overrides.raw_payload,
    },
    ...overrides,
  };
}

function buildIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: 'incident-1',
    title: 'AI incident',
    status: 'open',
    source: 'sentinelgrid_ai_shield',
    story_domains: ['ai', 'application', 'security'],
    raw_payload: {
      category: 'ai',
      ai: {
        app_id: 'copilot-finance',
        provider: 'openai',
        model: 'gpt-4.1',
      },
      ...overrides.raw_payload,
    },
    ...overrides,
  };
}

describe('responsePacks AI matching', () => {
  it('matches prompt injection alerts to the prompt-injection pack', () => {
    const alert = buildAlert({
      title: 'Prompt injection attempt detected in Finance Copilot',
      raw_payload: {
        category: 'ai',
        finding: { type: 'prompt_injection' },
        sg: { playbook_id: 'AI-PROMPT-INJECTION' },
        ai: {
          app_id: 'finance-copilot',
          provider: 'openai',
          model: 'gpt-4.1',
        },
      },
    });

    const matches = matchResponsePacksForAlert(alert, []);

    expect(matches[0]?.pack.id).toBe('ai_prompt_injection_containment');
    expect(matches.some((match) => match.pack.id === 'ai_data_leakage_response')).toBe(false);
  });

  it('matches data-exposure incidents to the AI leakage pack', () => {
    const incident = buildIncident({
      title: 'Sensitive AI data exposure in Sales Assistant',
      description: 'Sensitive customer data reached an external model provider.',
      recommended_playbook_key: 'AI-DATA-LEAK',
      raw_payload: {
        category: 'ai',
        finding: { type: 'sensitive_data_exposure' },
        sg: { playbook_id: 'AI-DATA-LEAK' },
        ai: {
          app_id: 'sales-assistant',
          provider: 'azure-openai',
          model: 'gpt-4.1',
        },
      },
    });

    const matches = matchResponsePacksForIncident(incident, []);

    expect(matches[0]?.pack.id).toBe('ai_data_leakage_response');
    expect(matches[0]?.reasons).toEqual(expect.arrayContaining(['sensitive data exposure finding']));
  });

  it('matches policy-violation alerts to the policy and tool-misuse pack', () => {
    const alert = buildAlert({
      title: 'AI policy violation in Support Assistant',
      description: 'Blocked an unsafe tool action after a guardrail policy decision.',
      raw_payload: {
        category: 'ai',
        finding: { type: 'policy_violation' },
        sg: { playbook_id: 'AI-POLICY-VIOLATION' },
        ai: {
          app_id: 'support-assistant',
          provider: 'anthropic',
          model: 'claude-sonnet',
          violation_reason: 'unsafe tool action',
        },
      },
    });

    const matches = matchResponsePacksForAlert(alert, []);

    expect(matches[0]?.pack.id).toBe('ai_policy_and_tool_misuse');
  });

  it('does not leave any response pack pointing at the stale AI Shield route', () => {
    expect(RESPONSE_PACKS.some((pack) => pack.operatorRoute === '/dashboard/ai-shield')).toBe(false);
  });
});
