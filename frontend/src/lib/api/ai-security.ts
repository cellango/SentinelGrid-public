// Types
export interface AiApp {
  id: string;
  org_id: string;
  name: string;
  environment: 'dev' | 'staging' | 'prod';
  description?: string;
  allowed_models?: string[];
  allow_external_providers: boolean;
  max_context_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface AiAppCreate {
  org_id: string;
  name: string;
  environment: string;
  description?: string;
  allowed_models?: string[];
  allow_external_providers?: boolean;
  max_context_tokens?: number;
}

export interface AiAppWithKey extends AiApp {
  api_key: string;
}

export interface AiPolicy {
  id: string;
  org_id: string;
  ai_app_id?: string;
  block_pii_outbound: boolean;
  block_secrets_outbound: boolean;
  block_external_llms: boolean;
  block_jailbreak_patterns: boolean;
  require_approval_for_high_risk_tools: boolean;
  created_at: string;
  updated_at: string;
}

export interface AiPolicyCreate {
  org_id: string;
  ai_app_id?: string;
  block_pii_outbound?: boolean;
  block_secrets_outbound?: boolean;
  block_external_llms?: boolean;
  block_jailbreak_patterns?: boolean;
  require_approval_for_high_risk_tools?: boolean;
}

export interface AiEvent {
  id: string;
  org_id: string;
  ai_app_id?: string;
  user_id?: string;
  provider?: string;
  model?: string;
  has_pii: boolean;
  has_secrets: boolean;
  prompt_injection_suspected: boolean;
  policy_decision?: string;
  tokens_in?: number;
  tokens_out?: number;
  created_at: string;
}

export interface ChatRequest {
  message: string;
  context?: any;
  conversation_history?: any[];
}

export interface ChatResponse {
  message: string;
  data?: any;
}

function aiShieldUnavailable(feature: string): never {
  throw new Error(
    `${feature} is not exposed through the launch-ready tenant product path yet. Use onboarding, AI Governance, and the shared operator queues instead.`
  );
}

// AI Apps API
export const aiAppsApi = {
  list: async (orgId: string): Promise<AiApp[]> => {
    aiShieldUnavailable('AI app registry');
  },

  create: async (data: AiAppCreate): Promise<AiAppWithKey> => {
    aiShieldUnavailable('AI app registry');
  },

  get: async (appId: string): Promise<AiApp> => {
    aiShieldUnavailable('AI app registry');
  },

  update: async (appId: string, data: Partial<AiAppCreate>): Promise<AiApp> => {
    aiShieldUnavailable('AI app registry');
  },

  delete: async (appId: string): Promise<void> => {
    aiShieldUnavailable('AI app registry');
  },

  regenerateKey: async (appId: string): Promise<{ api_key: string }> => {
    aiShieldUnavailable('AI app registry');
  },
};

// AI Policies API
export const aiPoliciesApi = {
  list: async (orgId: string, appId?: string): Promise<AiPolicy[]> => {
    aiShieldUnavailable('AI policy management');
  },

  create: async (data: AiPolicyCreate): Promise<AiPolicy> => {
    aiShieldUnavailable('AI policy management');
  },

  update: async (policyId: string, data: Partial<AiPolicyCreate>): Promise<AiPolicy> => {
    aiShieldUnavailable('AI policy management');
  },

  delete: async (policyId: string): Promise<void> => {
    aiShieldUnavailable('AI policy management');
  },
};

// AI Events API
export const aiEventsApi = {
  list: async (orgId: string, appId?: string, limit?: number): Promise<AiEvent[]> => {
    aiShieldUnavailable('AI event log');
  },
};

// AI Assistant API
export const aiAssistantApi = {
  chat: async (request: ChatRequest): Promise<ChatResponse> => {
    aiShieldUnavailable('AI security assistant');
  },
};

// Combined export
export const aiSecurityApi = {
  apps: aiAppsApi,
  policies: aiPoliciesApi,
  events: aiEventsApi,
  assistant: aiAssistantApi,
};

export default aiSecurityApi;
