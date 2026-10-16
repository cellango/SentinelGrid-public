import axios from 'axios';
import { apiClient } from './client';
import {
  type CanonicalEntityRef,
  type CanonicalEvidenceRef,
  type CanonicalStoryDomain,
  type CanonicalStorySummary,
  normalizeStoryContext,
  summarizeStoryContext,
} from '@/lib/security/story';

export interface Incident {
  id: string;
  tenant_id?: string;
  source?: string;
  external_id?: string;
  title: string;
  status: string;
  description?: string;
  severity?: string;
  phase?: string;
  assignee?: string;
  assigned_to?: string;
  sla?: string;
  due_date?: string | null;
  ticket_id?: string;
  external_ticket_id?: string;
  external_ticket_provider?: string;
  related_detections?: { id: string; title?: string; severity?: string }[];
  entities?: CanonicalEntityRef[];
  evidence?: CanonicalEvidenceRef[];
  story_domains?: CanonicalStoryDomain[];
  story_summary?: CanonicalStorySummary;
  timeline?: { ts: string; text: string; actor?: string }[];
  nist_controls?: any;
  mitre_tactics?: any;
  mitre_techniques?: any;
  cve_ids?: string[];
  exploit_indicators?: any;
  raw_payload?: any;
  created_at?: string;
  updated_at?: string;
  detection_rule_id?: string;
  detection_rule_version_id?: string;
  playbook_version_id?: string;
  recommended_playbook?: string;
  recommended_playbook_id?: string;
  recommended_playbook_key?: string;
}

export interface IncidentUpdatePayload {
  status?: string;
  severity?: string;
  phase?: string;
  assigned_to?: string | null;
  due_date?: string | null;
  description?: string | null;
  comment?: string | null;
  timeline_event?: string | null;
}

export interface SocCaseTaskSummary {
  id: string;
  tenant_id: string;
  incident_id?: string | null;
  case_id?: string | null;
  agent_id: string;
  task_type: string;
  priority: string;
  status: string;
  payload: Record<string, any>;
  context: Record<string, any>;
  result?: Record<string, any> | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SocPlaybookRecommendation {
  playbook_id?: string | null;
  playbook_key?: string | null;
  playbook_name: string;
  rank: number;
  confidence: number;
  rationale: string[];
  mapped_response_pack_id?: string | null;
  automation_mode: 'manual_review' | 'approval_required' | 'automated';
  status?: 'recommended' | 'accepted' | 'rejected' | 'executed' | 'skipped';
}

export interface SocActionRecommendation {
  action_id: string;
  action_type: string;
  label: string;
  description: string;
  risk_level: 'informational' | 'investigative' | 'low' | 'medium' | 'high' | 'critical';
  requires_approval: boolean;
  recommended_owner_role: 'L1' | 'L2' | 'L3' | 'SOC_MANAGER' | 'SOC_AI_AGENT' | 'HUMAN_OWNER';
  evidence_basis: string[];
  expected_outcome?: string | null;
  rollback_expectation?: string | null;
  status: 'recommended' | 'accepted' | 'rejected' | 'executed' | 'skipped';
  supporting_playbook_id?: string | null;
  supporting_playbook_key?: string | null;
}

export interface SocDocumentationBundle {
  template_kind:
    | 'triage_note'
    | 'investigation_update'
    | 'containment_recommendation'
    | 'post_action_update'
    | 'closure_ready';
  incident_note_draft: string;
  ticket_update_draft: string;
  timeline_event_draft: string;
  analyst_handoff_draft?: string | null;
  closure_checklist: string[];
}

export interface SocRecommendationOutput {
  recommendation_id: string;
  generated_at: string;
  case_summary: string;
  response_pack_id: string;
  response_pack_label: string;
  recommended_playbooks: SocPlaybookRecommendation[];
  recommended_actions: SocActionRecommendation[];
  missing_evidence: string[];
  proposed_phase?: string | null;
  proposed_status?: string | null;
  incident_note_draft?: string | null;
  ticket_update_draft?: string | null;
  timeline_event_draft?: string | null;
  analyst_handoff_draft?: string | null;
  closure_checklist: string[];
  documentation_bundle?: SocDocumentationBundle | null;
  confidence: number;
  rationale: string[];
}

export interface IncidentSocCaseState {
  tenant_id: string;
  incident_id: string;
  case_id?: string | null;
  case_context?: Record<string, any> | null;
  case_memory?: Record<string, any> | null;
  latest_recommendation?: SocRecommendationOutput | null;
  recommendation_versions: SocRecommendationOutput[];
  recent_tasks: SocCaseTaskSummary[];
}

function normalizeSocRecommendation(data: any): SocRecommendationOutput {
  return {
    ...data,
    closure_checklist: data?.closure_checklist || [],
    documentation_bundle: data?.documentation_bundle || null,
    recommended_playbooks: data?.recommended_playbooks || [],
    recommended_actions: data?.recommended_actions || [],
    missing_evidence: data?.missing_evidence || [],
    rationale: data?.rationale || [],
  };
}

export interface IncidentSocFeedbackPayload {
  recommendation_id: string;
  feedback_type:
    | 'accepted_recommendation'
    | 'rejected_recommendation'
    | 'edited_note'
    | 'playbook_override'
    | 'response_pack_override'
    | 'incorrect_recommendation';
  actor_id: string;
  actor_role: 'L1' | 'L2' | 'L3' | 'SOC_MANAGER' | 'SOC_AI_AGENT' | 'HUMAN_OWNER';
  accepted: boolean;
  action_id?: string | null;
  playbook_id?: string | null;
  playbook_key?: string | null;
  playbook_name?: string | null;
  notes?: string | null;
}

function normalizeIncident(inc: any): Incident {
  const rp = inc.raw_payload || {};
  const recommended_playbook =
    inc.recommended_playbook ||
    inc.recommended_playbook_id ||
    inc.recommended_playbook_key ||
    rp.recommended_playbook ||
    rp.recommended_playbook_id ||
    rp.recommended_playbook_key ||
    rp.sg?.playbook_id ||
    rp.playbook_id;
  const recommended_playbook_id =
    inc.recommended_playbook_id ||
    rp.recommended_playbook_id ||
    recommended_playbook ||
    inc.recommended_playbook_key;
  const recommended_playbook_key =
    inc.recommended_playbook_key ||
    rp.recommended_playbook_key ||
    rp.sg?.playbook_id ||
    rp.playbook_id ||
    inc.recommended_playbook_id;
  const relatedDetections =
    inc.related_detections ||
    (Array.isArray(rp.related_alert_ids)
      ? rp.related_alert_ids.map((id: any) => ({ id: String(id) }))
      : Array.isArray(rp.detections)
        ? rp.detections.map((d: any) => ({
            id: String(d?.id || d),
            title: typeof d === 'object' ? d?.title : undefined,
            severity: typeof d === 'object' ? d?.severity : undefined,
          }))
        : undefined);
  const timeline =
    inc.timeline ||
    (Array.isArray(rp.audit)
      ? rp.audit
      : Array.isArray(rp.timeline)
        ? rp.timeline
        : Array.isArray(rp.events)
          ? rp.events.map((e: any) => ({ ts: e.ts || e.timestamp, text: e.text || e.event_type }))
          : undefined);
  const assignedTo = inc.assigned_to || inc.assignee || rp.assigned_to || rp.assignee || rp.owner;
  const storyContext = normalizeStoryContext({
    rawPayload: rp,
    entities: inc.entities,
    evidence: inc.evidence,
    storyDomains: inc.story_domains,
    assetId: rp.asset_id,
    userIdentifier: rp.user_identifier,
    detectionRuleId: inc.detection_rule_id || rp.detection_rule_id,
    detectionRuleVersionId: inc.detection_rule_version_id || rp.detection_rule_version_id,
    playbookId: rp.playbook_id || rp?.sg?.playbook_id,
    playbookVersionId: inc.playbook_version_id || rp.playbook_version_id,
    relatedDetections: relatedDetections,
    ticketId: inc.ticket_id || rp.ticket_id,
    externalTicketId: inc.external_ticket_id || rp.external_ticket_id,
    externalTicketProvider: inc.external_ticket_provider || rp.external_ticket_provider,
    cveIds: inc.cve_ids,
  });
  const storySummary = inc.story_summary || summarizeStoryContext(storyContext);

  return {
    ...inc,
    description: inc.description || rp.description || rp.summary,
    phase: inc.phase || rp.phase || rp.workflow_state || inc.status,
    assignee: assignedTo,
    assigned_to: assignedTo,
    sla: inc.sla || rp.sla || rp.sla_minutes,
    due_date: inc.due_date || rp.due_date || rp.sla_due_at || null,
    ticket_id: inc.ticket_id || rp.ticket_id,
    external_ticket_id: inc.external_ticket_id || rp.external_ticket_id,
    external_ticket_provider: inc.external_ticket_provider || rp.external_ticket_provider,
    related_detections: relatedDetections,
    entities: storyContext.entities,
    evidence: storyContext.evidence,
    story_domains: storyContext.story_domains,
    story_summary: storySummary,
    timeline,
    detection_rule_id: inc.detection_rule_id || rp.detection_rule_id,
    detection_rule_version_id: inc.detection_rule_version_id || rp.detection_rule_version_id,
    playbook_version_id: inc.playbook_version_id || rp.playbook_version_id,
    recommended_playbook,
    recommended_playbook_id,
    recommended_playbook_key,
  };
}

export async function listIncidents(params?: {
  status?: string;
  severity?: string;
  limit?: number;
  offset?: number;
}): Promise<{ items: Incident[]; total: number; limit?: number; offset?: number }> {
  const response = await apiClient.get('/incidents', { params });
  const data = response.data || {};
  return {
    items: (data.items || []).map(normalizeIncident),
    total: data.total ?? (data.items ? data.items.length : 0),
    limit: data.limit,
    offset: data.offset,
  };
}

export async function getIncident(id: string): Promise<Incident> {
  const response = await apiClient.get(`/incidents/${id}`);
  return normalizeIncident(response.data || {});
}

export async function updateIncident(id: string, updates: IncidentUpdatePayload): Promise<Incident> {
  const response = await apiClient.patch(`/incidents/${id}`, updates);
  return normalizeIncident(response.data || {});
}

export async function getIncidentSocCaseState(id: string): Promise<IncidentSocCaseState | null> {
  try {
    const response = await apiClient.get(`/incidents/${id}/soc-case`);
    const data = response.data || {};
    return {
      tenant_id: data.tenant_id,
      incident_id: data.incident_id,
      case_id: data.case_id,
      case_context: data.case_context || null,
      case_memory: data.case_memory || null,
      latest_recommendation: data.latest_recommendation
        ? normalizeSocRecommendation(data.latest_recommendation)
        : null,
      recommendation_versions: (data.recommendation_versions || []).map(normalizeSocRecommendation),
      recent_tasks: data.recent_tasks || [],
    };
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function submitIncidentSocFeedback(
  id: string,
  payload: IncidentSocFeedbackPayload
): Promise<IncidentSocCaseState> {
  const response = await apiClient.post(`/incidents/${id}/soc-case/feedback`, payload);
  const data = response.data || {};
  return {
    tenant_id: data.tenant_id,
    incident_id: data.incident_id,
    case_id: data.case_id,
    case_context: data.case_context || null,
    case_memory: data.case_memory || null,
    latest_recommendation: data.latest_recommendation
      ? normalizeSocRecommendation(data.latest_recommendation)
      : null,
    recommendation_versions: (data.recommendation_versions || []).map(normalizeSocRecommendation),
    recent_tasks: data.recent_tasks || [],
  };
}
