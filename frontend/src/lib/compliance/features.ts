function envFlag(value: string | undefined) {
  return ['1', 'true', 'yes', 'on'].includes((value || '').trim().toLowerCase());
}

export const complianceFeatureFlags = {
  multiFramework: envFlag(process.env.NEXT_PUBLIC_COMPLIANCE_MULTI_FRAMEWORK_ENABLED),
  evidenceRepository: envFlag(process.env.NEXT_PUBLIC_COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED),
  complianceAgent: envFlag(process.env.NEXT_PUBLIC_COMPLIANCE_AGENT_ENABLED),
};

export function getComplianceRuntimeLabels() {
  return {
    dashboardTitle: complianceFeatureFlags.multiFramework
      ? 'Compliance Dashboard'
      : 'SOC 2 Readiness Dashboard',
    dashboardDescription: complianceFeatureFlags.multiFramework
      ? 'Track selected frameworks, evidence, and report readiness from live security signals.'
      : 'Use mapped detections and control checks for SOC 2 readiness and trust reporting.',
    reportsTitle: complianceFeatureFlags.evidenceRepository
      ? 'Compliance Reports'
      : 'Trust & SOC 2 Reports',
    reportsDescription: complianceFeatureFlags.evidenceRepository
      ? 'Generate compliance exports from selected frameworks, reviewed evidence, and coverage snapshots.'
      : 'Generate readiness and customer trust exports from live detections and control checks.',
    evidenceMetricLabel: complianceFeatureFlags.evidenceRepository
      ? 'Evidence items'
      : 'Report-ready signals',
    evidenceMetricDescription: complianceFeatureFlags.evidenceRepository
      ? 'Reviewed objects available for audit packets'
      : 'Signals currently available for readiness exports',
  };
}

