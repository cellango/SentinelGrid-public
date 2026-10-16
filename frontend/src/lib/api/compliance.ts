import { apiClient } from './client';

export interface ComplianceReport {
  tenant_id: string;
  report_date: string;
  total_entitlements: number;
  active_entitlements: number;
  revoked_entitlements: number;
  expired_entitlements: number;
  pending_review: number;
  users_with_entitlements: number;
  entitlements_by_resource_type: Record<string, number>;
  entitlements_by_action: Record<string, number>;
}

export interface AuditTrailEntry {
  entitlement_id: string;
  resource_type: string;
  resource_id: string;
  action: string;
  status: string;
  updated_at?: string;
  granted_at?: string;
}

export interface AuditTrailResponse {
  tenant_id?: string;
  start_date?: string;
  end_date?: string;
  results: AuditTrailEntry[];
  count: number;
  limit?: number;
  offset?: number;
}

export interface OrphanedEntitlement {
  id: string;
  granted_to_id: string;
  granted_to_type: string;
  resource_type: string;
  resource_id: string;
  action: string;
  expired_at?: string;
}

export interface OrphanedEntitlementsResponse {
  tenant_id: string;
  orphaned_count: number;
  entitlements: OrphanedEntitlement[];
}

export interface ComplianceSignal {
  id: string;
  title: string;
  description?: string;
  status?: string;
  severity?: string;
  source?: string;
  source_type?: string;
  source_label?: string;
  detected_at?: string;
  href?: string;
  detection_rule_id?: string;
  recommended_playbook?: string | null;
  nist_control_id?: string | null;
}

export interface CompliancePlaybookRef {
  id: string;
  name: string;
  key?: string;
  href?: string;
}

export type ComplianceCoverageStatus =
  | 'not_started'
  | 'needs_evidence'
  | 'partially_supported'
  | 'ready_for_review'
  | 'accepted'
  | 'exception'
  | 'not_applicable';

export type ComplianceCoverageSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface ComplianceCriterion {
  id: string;
  title: string;
  description?: string;
  status: 'compliant' | 'partial' | 'non_compliant' | 'not_assessed';
  coverage_status?: ComplianceCoverageStatus;
  coverage_confidence?: number;
  coverage_severity?: ComplianceCoverageSeverity | null;
  coverage_trace?: string[];
  coverage_gaps?: Array<Record<string, unknown>>;
  open_findings: number;
  total_findings: number;
  detection_count: number;
  control_check_count: number;
  playbook_count: number;
  playbook_execution_count: number;
  evidence_items: number;
  mapped_nist_controls: string[];
  key_detections: ComplianceSignal[];
  control_checks: ComplianceSignal[];
  supporting_playbooks: CompliancePlaybookRef[];
  last_activity?: string | null;
}

export interface ComplianceCoverageSummary {
  tenant_id: string;
  total_criteria: number;
  open_criteria: number;
  total_findings: number;
  open_findings: number;
  status: string;
  mapped_detections: number;
  control_checks: number;
  playbooks: number;
  automated_responses: number;
  evidence_items: number;
  last_assessment?: string | null;
}

export interface ComplianceReportingSummary {
  criteria_ready: number;
  criteria_partial: number;
  criteria_needing_attention: number;
  criteria_not_assessed: number;
  key_detection_count: number;
  control_check_count: number;
  playbook_count: number;
  playbook_execution_count: number;
  reportable_evidence_items: number;
  top_detection_sources: Array<{ source: string; count: number }>;
}

export interface ComplianceFrameworkStarterPackMetricSummary {
  criteria_ready: number;
  criteria_needing_attention: number;
  mapped_signals: number;
  evidence_items: number;
}

export interface ComplianceFrameworkStarterPackFocusArea {
  key: string;
  title: string;
  description: string;
  status: 'ready' | 'needs_attention' | 'starter';
  detail: string;
}

export interface ComplianceFrameworkStarterPackAction {
  title: string;
  description: string;
  href: string;
}

export interface ComplianceFrameworkStarterPack {
  framework_key: 'soc2' | 'iso27001';
  framework_name: string;
  launch_state: 'live' | 'starter';
  score_label: string;
  score: number;
  summary: string;
  note: string;
  metrics: ComplianceFrameworkStarterPackMetricSummary;
  artifact_template_keys: string[];
  focus_areas: ComplianceFrameworkStarterPackFocusArea[];
  quick_actions: ComplianceFrameworkStarterPackAction[];
}

export interface ComplianceFrameworkCatalogSummary {
  id: string;
  framework_id: string;
  framework_code: string;
  framework_name: string;
  version?: string;
  description?: string;
  runtime_support: 'readiness' | 'catalog' | string;
  source: string;
  category_count: number;
  control_count: number;
  related_framework?: string | null;
}

export interface ComplianceFrameworkCatalogResponse {
  items: ComplianceFrameworkCatalogSummary[];
  count: number;
  source: string;
  schema_tables: string[];
}

export interface ComplianceFrameworkCategory {
  code: string;
  name: string;
  description?: string | null;
  control_count: number;
}

export interface ComplianceFrameworkDetail extends ComplianceFrameworkCatalogSummary {
  categories: ComplianceFrameworkCategory[];
  additional_features?: Record<string, unknown>;
}

export interface ComplianceFrameworkControl {
  id: string;
  framework_id: string;
  control_id: string;
  title: string;
  description?: string | null;
  category: {
    code: string;
    name: string;
  };
  priority?: string | null;
  coverage_level?: string | null;
  sentinelgrid_features: string[];
  implementation_specs: string[];
  evidence_requirements: unknown[];
}

export interface ComplianceFrameworkControlsResponse {
  framework_id: string;
  framework_code: string;
  framework_name: string;
  items: ComplianceFrameworkControl[];
  count: number;
  source: string;
}

export type ComplianceFrameworkSelectionStatus = 'active' | 'inactive' | 'evaluating';

export interface ComplianceFrameworkSelection {
  framework_id: string;
  framework_code?: string | null;
  framework_name: string;
  runtime_support: string;
  control_count: number;
  status: ComplianceFrameworkSelectionStatus;
  priority?: number | null;
  target_date?: string | null;
  selected_by?: string | null;
  selected_at?: string | null;
  updated_at?: string | null;
  source: string;
}

export interface ComplianceFrameworkSelectionOption {
  framework_id: string;
  framework_code: string;
  framework_name: string;
  runtime_support: string;
  control_count: number;
  description?: string;
}

export interface ComplianceFrameworkSelectionsResponse {
  tenant_id: string;
  items: ComplianceFrameworkSelection[];
  count: number;
  available_frameworks: ComplianceFrameworkSelectionOption[];
  source: string;
}

export interface ComplianceFrameworkSelectionUpdate {
  framework_id: string;
  status?: ComplianceFrameworkSelectionStatus;
  priority?: number | null;
  target_date?: string | null;
}

export interface Soc2CoverageResponse {
  summary: ComplianceCoverageSummary;
  controls: ComplianceCriterion[];
  status: string;
  reporting_summary: ComplianceReportingSummary;
  key_detections: ComplianceSignal[];
  control_checks: ComplianceSignal[];
  overall_score: number;
  coverage_model?: {
    framework_id: string;
    status: string;
    status_counts: Record<string, number>;
    average_confidence: number;
    generated_at: string;
  };
}

export interface ComplianceControlCoverage {
  id: string;
  framework_id: string;
  control_id: string;
  title: string;
  description?: string | null;
  status: ComplianceCoverageStatus;
  severity?: ComplianceCoverageSeverity | null;
  confidence: number;
  signals: Array<Record<string, unknown>>;
  gaps: Array<Record<string, unknown>>;
  evidence_requirements: Array<Record<string, unknown>>;
  last_activity?: string | null;
  trace: string[];
  metadata: Record<string, unknown>;
  framework_name?: string;
  runtime_support?: string;
  selection_status?: string;
}

export interface ComplianceFrameworkCoverage {
  tenant_id: string;
  framework_id: string;
  framework_code?: string | null;
  framework_name: string;
  runtime_support: string;
  selection_status: string;
  selection_source?: string | null;
  status: ComplianceCoverageStatus;
  status_counts: Record<string, number>;
  average_confidence: number;
  control_count: number;
  returned_control_count: number;
  limit: number;
  offset: number;
  generated_at: string;
  controls: ComplianceControlCoverage[];
}

export interface ComplianceMultiFrameworkCoverageResponse {
  tenant_id: string;
  items: ComplianceFrameworkCoverage[];
  count: number;
  limit: number;
  offset: number;
  source: string;
}

export interface ComplianceControlStatusResponse {
  tenant_id: string;
  control_id: string;
  framework_id?: string | null;
  items: ComplianceControlCoverage[];
  count: number;
  source: string;
}

export interface ComplianceDashboardResponse {
  overall_stats: {
    overall_score: number;
    controls_implemented: number;
    total_controls: number;
    evidence_items: number;
    last_assessment?: string | null;
    mapped_detections: number;
    control_checks: number;
  };
  soc2: Soc2CoverageResponse;
  reporting_summary: ComplianceReportingSummary;
  priority_criteria: ComplianceCriterion[];
  key_detections: ComplianceSignal[];
  control_checks: ComplianceSignal[];
  framework_starter_packs: ComplianceFrameworkStarterPack[];
  framework_coverage?: ComplianceMultiFrameworkCoverageResponse;
  selected_frameworks?: Array<Omit<ComplianceFrameworkCoverage, 'controls'>>;
}

export interface ComplianceCapabilitiesResponse {
  runtime_mode: 'soc2_readiness' | string;
  capabilities: {
    soc2_readiness: boolean;
    framework_starter_packs: boolean;
    multi_framework_selection: boolean;
    durable_evidence_repository: boolean;
    compliance_agent_workflows: boolean;
  };
  compatibility_endpoints: string[];
  stub_endpoints: string[];
  deprecated_endpoints?: Array<{
    path: string;
    replacement?: string;
    reason?: string;
  }>;
  truth_labels: {
    dashboard_title: string;
    reports_title: string;
    evidence_label: string;
  };
  admin_control_paths?: {
    readiness: string;
    settings: string;
  };
  admin_controls?: Array<{
    key: string;
    label: string;
    env_var: string;
    feature_flag_key: string;
  }>;
  known_limitations?: Array<{
    framework_id: string;
    support_level: string;
    limitations: string[];
  }>;
}

export interface ComplianceLaunchControl {
  key: string;
  label: string;
  description: string;
  env_var: string;
  feature_flag_key: string;
  platform_enabled: boolean;
  requested_enabled: boolean;
  effective_enabled: boolean;
  mutable_by_admin: boolean;
  blocked_reason?: string | null;
}

export interface ComplianceAdminSettingsResponse {
  tenant_id: string;
  source: string;
  launch_version: string;
  updated_at?: string | null;
  controls: Record<string, ComplianceLaunchControl>;
}

export interface ComplianceFrameworkLimitation {
  framework_id: string;
  framework_name: string;
  support_level: string;
  available: string[];
  limitations: string[];
}

export interface ComplianceLaunchReadinessResponse {
  tenant_id: string;
  launch_version: string;
  readiness_status: string;
  product_copy: Record<string, string>;
  known_limitations: ComplianceFrameworkLimitation[];
  admin_settings: ComplianceAdminSettingsResponse;
  demo_seed: {
    script: string;
    dry_run_command: string;
    apply_command: string;
  };
  go_no_go_review: {
    artifact: string;
    required_owners: string[];
    decision: string;
  };
}

export interface ComplianceAdminSettingsUpdateRequest {
  multi_framework_selection?: boolean;
  durable_evidence_repository?: boolean;
  compliance_agent_workflows?: boolean;
}

export type ComplianceEvidenceType =
  | 'configuration'
  | 'audit_log'
  | 'policy_document'
  | 'test_result'
  | 'screenshot'
  | 'export'
  | 'api_response';

export interface ComplianceEvidenceCollectionResponse {
  control_id: string;
  tenant_id?: string | null;
  evidence: Record<string, unknown>;
  repository?: {
    status: string;
    evidence_items: ComplianceEvidenceItem[];
    collection_tasks: ComplianceEvidenceCollectionTask[];
    errors: Array<Record<string, unknown>>;
  };
  collected_at: string;
}

export type ComplianceEvidenceSensitivity = 'public' | 'internal' | 'confidential' | 'restricted';
export type ComplianceEvidenceReviewStatus =
  | 'pending'
  | 'ready_for_review'
  | 'accepted'
  | 'rejected'
  | 'needs_changes'
  | 'expired'
  | 'retired'
  | 'superseded';

export interface ComplianceEvidenceControlLink {
  id?: string;
  tenant_id?: string;
  evidence_item_id?: string;
  control_id: string;
  control_ref?: string | null;
  control_name?: string | null;
  framework_id?: string | null;
  framework_code?: string | null;
  framework_name?: string | null;
  evidence_requirement_id?: string | null;
  package_id?: string | null;
  link_type?: 'supports' | 'contradicts' | 'context' | 'exception';
  status?: string;
  rationale?: string | null;
  linked_by?: string | null;
  linked_at?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ComplianceEvidenceReview {
  id: string;
  tenant_id: string;
  evidence_item_id?: string | null;
  package_id?: string | null;
  control_link_id?: string | null;
  review_status: ComplianceEvidenceReviewStatus;
  reviewer: string;
  reviewed_at: string;
  review_notes?: string | null;
  rejection_reason?: string | null;
  expires_at?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ComplianceEvidenceItem {
  id: string;
  tenant_id: string;
  realm_name?: string;
  package_id?: string | null;
  control_id?: string | null;
  evidence_type: string;
  title: string;
  description?: string | null;
  source_system: string;
  source_resource_id: string;
  collector: string;
  collection_method: string;
  collected_at: string;
  valid_from: string;
  valid_until: string;
  hash_sha256: string;
  storage_uri: string;
  summary: string;
  sensitivity: ComplianceEvidenceSensitivity;
  review_status: ComplianceEvidenceReviewStatus;
  metadata?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
  integrity_metadata?: Record<string, unknown>;
  retention_until?: string | null;
  created_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  idempotency_key?: string | null;
  control_links?: ComplianceEvidenceControlLink[];
  reviews?: ComplianceEvidenceReview[];
}

export interface ComplianceEvidenceListResponse {
  tenant_id: string;
  items: ComplianceEvidenceItem[];
  count: number;
  limit: number;
  offset: number;
  filters?: Record<string, unknown>;
  source?: string;
}

export interface ComplianceEvidenceCreateRequest {
  tenant_id?: string;
  realm_name?: string;
  package_id?: string;
  evidence_type: string;
  title: string;
  description?: string;
  source_system: string;
  source_resource_id: string;
  collector: string;
  collection_method: string;
  collected_at?: string;
  valid_from: string;
  valid_until: string;
  hash_sha256: string;
  storage_uri: string;
  summary: string;
  sensitivity?: ComplianceEvidenceSensitivity;
  review_status?: ComplianceEvidenceReviewStatus;
  created_by?: string;
  control_links?: ComplianceEvidenceControlLink[];
  metadata?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
  integrity_metadata?: Record<string, unknown>;
  idempotency_key?: string;
}

export interface ComplianceEvidencePackage {
  id: string;
  tenant_id: string;
  realm_name?: string;
  package_name: string;
  package_type?: string;
  framework_id?: string | null;
  report_period_start: string;
  report_period_end: string;
  status?: string;
  review_status?: ComplianceEvidenceReviewStatus;
  summary?: string | null;
  description?: string | null;
  sensitivity?: ComplianceEvidenceSensitivity;
  metadata?: Record<string, unknown>;
  manifest?: Record<string, unknown>;
  coverage_snapshot?: Record<string, unknown>;
  evidence_item_count?: number;
  items?: ComplianceEvidenceItem[];
  exports?: ComplianceEvidenceExport[];
}

export interface ComplianceEvidencePackageListResponse {
  tenant_id: string;
  items: ComplianceEvidencePackage[];
  count: number;
  limit: number;
  offset: number;
  filters?: Record<string, unknown>;
  source?: string;
}

export interface ComplianceEvidencePackageCreateRequest {
  tenant_id?: string;
  realm_name?: string;
  package_name: string;
  framework_id?: string;
  report_period_start: string;
  report_period_end: string;
  package_type?: string;
  summary?: string;
  description?: string;
  sensitivity?: ComplianceEvidenceSensitivity;
  metadata?: Record<string, unknown>;
  evidence_item_ids?: string[];
}

export interface ComplianceEvidenceExport {
  id: string;
  tenant_id: string;
  package_id: string;
  export_format: 'pdf' | 'zip' | 'csv';
  status: 'requested' | 'running' | 'completed' | 'failed' | 'expired' | 'deleted';
  requested_by: string;
  requested_at: string;
  completed_at?: string | null;
  storage_uri?: string | null;
  hash_sha256?: string | null;
  file_size_bytes?: number | null;
  include_sensitive: boolean;
  manifest?: Record<string, unknown>;
  expires_at?: string | null;
  retention_until?: string | null;
  immutable_after?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ComplianceEvidenceHashResponse {
  hash_algorithm: 'sha256';
  hash_sha256: string;
  byte_length: number;
}

export interface ComplianceEvidenceIntegrityVerification {
  id?: string;
  tenant_id?: string;
  evidence_item_id?: string;
  verification_status: 'verified' | 'mismatch' | 'missing_observed_hash';
  verification_method?: string;
  expected_hash_sha256?: string;
  observed_hash_sha256?: string | null;
  verified_by?: string;
  verified_at?: string;
  metadata?: Record<string, unknown>;
}

export interface ComplianceEvidenceRetentionPolicy {
  id: string;
  tenant_id: string;
  framework_id?: string | null;
  subject_type: 'evidence_item' | 'evidence_package' | 'evidence_export' | 'collection_task';
  retention_days: number;
  policy_name: string;
  description?: string | null;
  legal_hold: boolean;
  metadata?: Record<string, unknown>;
}

export interface ComplianceEvidenceRetentionPolicyListResponse {
  tenant_id: string;
  items: ComplianceEvidenceRetentionPolicy[];
  count: number;
  filters?: Record<string, unknown>;
  source?: string;
}

export interface ComplianceEvidenceCollectionTask {
  id: string;
  tenant_id: string;
  realm_name?: string;
  package_id?: string | null;
  task_name: string;
  task_type: string;
  status:
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'cancelled'
    | 'needs_connector'
    | 'manual_evidence_required';
  source_system?: string | null;
  source_resource_id?: string | null;
  collector?: string | null;
  collection_method?: string | null;
  requested_by?: string | null;
  due_at?: string | null;
  error_message?: string | null;
  metadata?: Record<string, unknown>;
  retention_until?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  idempotency_key?: string | null;
  idempotent_replay?: boolean;
}

export interface ComplianceEvidenceCollectionTaskListResponse {
  tenant_id: string;
  items: ComplianceEvidenceCollectionTask[];
  count: number;
  limit: number;
  offset: number;
  filters?: Record<string, unknown>;
  source?: string;
}

export type ComplianceAgentRecommendationState =
  | 'draft'
  | 'proposed'
  | 'accepted'
  | 'rejected'
  | 'superseded';

export type ComplianceAgentRecommendationPriority = 'critical' | 'high' | 'medium' | 'low';

export interface ComplianceAgentProposedAction {
  action?: string;
  tool?: string;
  requires_approval?: boolean;
  arguments?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ComplianceAgentRecommendation {
  id: string;
  tenant_id: string;
  agent_task_id?: string | null;
  trigger_type: string;
  recommendation_type: string;
  state: ComplianceAgentRecommendationState;
  priority: ComplianceAgentRecommendationPriority;
  source_type: string;
  source_id?: string | null;
  framework_id?: string | null;
  control_id?: string | null;
  evidence_item_id?: string | null;
  evidence_package_id?: string | null;
  report_id?: string | null;
  title: string;
  summary: string;
  proposed_actions: ComplianceAgentProposedAction[];
  requires_approval: boolean;
  created_by?: string | null;
  decided_by?: string | null;
  decided_at?: string | null;
  decision_notes?: string | null;
  superseded_by?: string | null;
  idempotency_key?: string | null;
  metadata?: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ComplianceAgentRecommendationListResponse {
  tenant_id: string;
  items: ComplianceAgentRecommendation[];
  count: number;
  limit: number;
  offset: number;
}

export const complianceApi = {
  getReport: async (tenantId: string): Promise<ComplianceReport> => {
    const response = await apiClient.get('/compliance/report', {
      params: { tenant_id: tenantId },
    });
    return response.data;
  },

  getAuditTrail: async (params: {
    tenant_id: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditTrailResponse> => {
    const response = await apiClient.get('/compliance/audit-trail', { params });
    return response.data;
  },

  getOrphanedEntitlements: async (tenantId: string): Promise<OrphanedEntitlementsResponse> => {
    const response = await apiClient.get('/compliance/orphaned-entitlements', {
      params: { tenant_id: tenantId },
    });
    return response.data;
  },

  collectEvidence: async (request: {
    control_id: string;
    evidence_types: ComplianceEvidenceType[];
    tenant_id?: string;
  }): Promise<ComplianceEvidenceCollectionResponse> => {
    const response = await apiClient.post('/compliance/evidence/collect', request);
    return response.data;
  },
};

export async function listComplianceEvidence(params?: {
  tenant_id?: string;
  framework_id?: string;
  control_id?: string;
  source_system?: string;
  review_status?: ComplianceEvidenceReviewStatus;
  package_id?: string;
  expires_before?: string;
  expires_after?: string;
  limit?: number;
  offset?: number;
}): Promise<ComplianceEvidenceListResponse> {
  const response = await apiClient.get('/compliance/evidence', { params });
  return response.data;
}

export async function createComplianceEvidence(
  request: ComplianceEvidenceCreateRequest
): Promise<ComplianceEvidenceItem> {
  const response = await apiClient.post('/compliance/evidence', request);
  return response.data;
}

export async function getComplianceEvidence(evidenceId: string): Promise<ComplianceEvidenceItem> {
  const response = await apiClient.get(`/compliance/evidence/${encodeURIComponent(evidenceId)}`);
  return response.data;
}

export async function reviewComplianceEvidence(
  evidenceId: string,
  request: {
    tenant_id?: string;
    review_status: 'accepted' | 'rejected' | 'needs_changes' | 'expired' | 'retired';
    reviewer?: string;
    review_notes?: string;
    rejection_reason?: string;
    expires_at?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<{ evidence: ComplianceEvidenceItem; review: ComplianceEvidenceReview; source?: string }> {
  const response = await apiClient.post(`/compliance/evidence/${encodeURIComponent(evidenceId)}/review`, request);
  return response.data;
}

export async function createComplianceEvidencePackage(
  request: ComplianceEvidencePackageCreateRequest
): Promise<ComplianceEvidencePackage> {
  const response = await apiClient.post('/compliance/evidence/packages', request);
  return response.data;
}

export async function listComplianceEvidencePackages(params?: {
  tenant_id?: string;
  framework_id?: string;
  status?: string;
  review_status?: ComplianceEvidenceReviewStatus;
  limit?: number;
  offset?: number;
}): Promise<ComplianceEvidencePackageListResponse> {
  const response = await apiClient.get('/compliance/evidence/packages', { params });
  return response.data;
}

export async function createComplianceEvidenceCollectionTask(request: {
  tenant_id?: string;
  realm_name?: string;
  package_id?: string;
  task_name: string;
  task_type: string;
  status?: ComplianceEvidenceCollectionTask['status'];
  source_system?: string;
  source_resource_id?: string;
  collector?: string;
  collection_method?: string;
  requested_by?: string;
  due_at?: string;
  error_message?: string;
  metadata?: Record<string, unknown>;
  idempotency_key?: string;
}): Promise<ComplianceEvidenceCollectionTask> {
  const response = await apiClient.post('/compliance/evidence/tasks', request);
  return response.data;
}

export async function listComplianceEvidenceCollectionTasks(params?: {
  tenant_id?: string;
  status?: ComplianceEvidenceCollectionTask['status'];
  task_type?: string;
  source_system?: string;
  package_id?: string;
  due_before?: string;
  due_after?: string;
  limit?: number;
  offset?: number;
}): Promise<ComplianceEvidenceCollectionTaskListResponse> {
  const response = await apiClient.get('/compliance/evidence/tasks', { params });
  return response.data;
}

export async function getComplianceEvidencePackage(packageId: string): Promise<ComplianceEvidencePackage> {
  const response = await apiClient.get(`/compliance/evidence/packages/${encodeURIComponent(packageId)}`);
  return response.data;
}

export async function exportComplianceEvidencePackage(
  packageId: string,
  request: {
    tenant_id?: string;
    export_format: 'pdf' | 'zip' | 'csv';
    requested_by?: string;
    include_sensitive?: boolean;
    manifest?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
  }
): Promise<ComplianceEvidenceExport> {
  const response = await apiClient.post(`/compliance/evidence/packages/${encodeURIComponent(packageId)}/export`, request);
  return response.data;
}

export async function calculateComplianceEvidenceHash(request: {
  content: string;
  encoding?: 'utf-8' | 'base64' | 'hex';
}): Promise<ComplianceEvidenceHashResponse> {
  const response = await apiClient.post('/compliance/evidence/hash', request);
  return response.data;
}

export async function verifyComplianceEvidenceIntegrity(
  evidenceId: string,
  request: {
    tenant_id?: string;
    observed_hash_sha256?: string;
    verification_method?: string;
    verified_by?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<{ evidence: ComplianceEvidenceItem; verification: ComplianceEvidenceIntegrityVerification; source?: string }> {
  const response = await apiClient.post(`/compliance/evidence/${encodeURIComponent(evidenceId)}/verify`, request);
  return response.data;
}

export async function listComplianceEvidenceRetentionPolicies(params?: {
  tenant_id?: string;
  framework_id?: string;
  subject_type?: ComplianceEvidenceRetentionPolicy['subject_type'];
}): Promise<ComplianceEvidenceRetentionPolicyListResponse> {
  const response = await apiClient.get('/compliance/evidence/retention-policies', { params });
  return response.data;
}

export async function upsertComplianceEvidenceRetentionPolicy(
  request: Omit<ComplianceEvidenceRetentionPolicy, 'id' | 'tenant_id' | 'legal_hold'> & {
    tenant_id?: string;
    legal_hold?: boolean;
  }
): Promise<ComplianceEvidenceRetentionPolicy> {
  const response = await apiClient.put('/compliance/evidence/retention-policies', request);
  return response.data;
}

export async function scheduleComplianceEvidenceRecollectionTask(
  evidenceId: string,
  request: {
    tenant_id?: string;
    reason?: 'expired' | 'expiring_soon' | 'stale' | 'manual_refresh';
    due_at?: string;
    task_status?: 'pending' | 'manual_evidence_required';
    requested_by?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<ComplianceEvidenceCollectionTask> {
  const response = await apiClient.post(`/compliance/evidence/${encodeURIComponent(evidenceId)}/recollection-task`, request);
  return response.data;
}

export async function finalizeComplianceEvidenceExport(
  packageId: string,
  exportId: string,
  request: {
    tenant_id?: string;
    status: 'completed' | 'failed';
    storage_uri?: string;
    hash_sha256?: string;
    file_size_bytes?: number;
    completed_at?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<ComplianceEvidenceExport> {
  const response = await apiClient.patch(
    `/compliance/evidence/packages/${encodeURIComponent(packageId)}/exports/${encodeURIComponent(exportId)}`,
    request
  );
  return response.data;
}

export async function retireComplianceEvidence(
  evidenceId: string,
  request: {
    tenant_id?: string;
    reason?: string;
    review_notes?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<ComplianceEvidenceItem> {
  const response = await apiClient.post(`/compliance/evidence/${encodeURIComponent(evidenceId)}/retire`, request);
  return response.data;
}

export async function deleteComplianceEvidence(evidenceId: string): Promise<ComplianceEvidenceItem> {
  const response = await apiClient.delete(`/compliance/evidence/${encodeURIComponent(evidenceId)}`);
  return response.data;
}

export async function getComplianceDashboard(): Promise<ComplianceDashboardResponse> {
  const response = await apiClient.get('/compliance/dashboard');
  return response.data;
}

export async function getComplianceCoverage(params?: {
  limit?: number;
  offset?: number;
}): Promise<ComplianceMultiFrameworkCoverageResponse> {
  const response = await apiClient.get('/compliance/coverage', { params });
  return response.data;
}

export async function getComplianceFrameworkCoverage(
  frameworkId: string,
  params?: { limit?: number; offset?: number }
): Promise<ComplianceFrameworkCoverage> {
  const response = await apiClient.get(`/compliance/frameworks/${encodeURIComponent(frameworkId)}/coverage`, { params });
  return response.data;
}

export async function getComplianceControlStatus(
  controlId: string,
  params?: { framework_id?: string }
): Promise<ComplianceControlStatusResponse> {
  const response = await apiClient.get(`/compliance/controls/${encodeURIComponent(controlId)}/status`, { params });
  return response.data;
}

export async function getComplianceCapabilities(): Promise<ComplianceCapabilitiesResponse> {
  const response = await apiClient.get('/compliance/capabilities');
  return response.data;
}

export async function getComplianceLaunchReadiness(): Promise<ComplianceLaunchReadinessResponse> {
  const response = await apiClient.get('/compliance/launch-readiness');
  return response.data;
}

export async function getComplianceAdminSettings(): Promise<ComplianceAdminSettingsResponse> {
  const response = await apiClient.get('/compliance/admin/settings');
  return response.data;
}

export async function updateComplianceAdminSettings(
  request: ComplianceAdminSettingsUpdateRequest
): Promise<ComplianceAdminSettingsResponse> {
  const response = await apiClient.put('/compliance/admin/settings', request);
  return response.data;
}

export async function listComplianceAgentRecommendations(params?: {
  state?: ComplianceAgentRecommendationState;
  trigger_type?: string;
  source_type?: string;
  framework_id?: string;
  control_id?: string;
  limit?: number;
  offset?: number;
}): Promise<ComplianceAgentRecommendationListResponse> {
  const response = await apiClient.get('/compliance/agent/recommendations', { params });
  return response.data;
}

export async function decideComplianceAgentRecommendation(
  recommendationId: string,
  request: {
    state: Extract<ComplianceAgentRecommendationState, 'accepted' | 'rejected' | 'superseded'>;
    decision_notes?: string;
    superseded_by?: string;
  }
): Promise<ComplianceAgentRecommendation> {
  const response = await apiClient.post(
    `/compliance/agent/recommendations/${encodeURIComponent(recommendationId)}/decision`,
    request
  );
  return response.data;
}

export async function getComplianceFrameworks(): Promise<ComplianceFrameworkCatalogResponse> {
  const response = await apiClient.get('/compliance/frameworks');
  return response.data;
}

export async function getComplianceFramework(frameworkId: string): Promise<ComplianceFrameworkDetail> {
  const response = await apiClient.get(`/compliance/frameworks/${encodeURIComponent(frameworkId)}`);
  return response.data;
}

export async function getComplianceFrameworkControls(
  frameworkId: string
): Promise<ComplianceFrameworkControlsResponse> {
  const response = await apiClient.get(`/compliance/frameworks/${encodeURIComponent(frameworkId)}/controls`);
  return response.data;
}

export async function getComplianceFrameworkSelections(): Promise<ComplianceFrameworkSelectionsResponse> {
  const response = await apiClient.get('/compliance/framework-selections');
  return response.data;
}

export async function updateComplianceFrameworkSelections(request: {
  tenant_id?: string;
  selections: ComplianceFrameworkSelectionUpdate[];
}): Promise<ComplianceFrameworkSelectionsResponse> {
  const response = await apiClient.put('/compliance/framework-selections', request);
  return response.data;
}

export async function getSoc2Coverage(): Promise<Soc2CoverageResponse> {
  const response = await apiClient.get('/compliance/soc2/coverage');
  return response.data;
}
