function loadFeatures() {
  return require('../features') as typeof import('../features');
}

describe('compliance feature flags', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    delete process.env.NEXT_PUBLIC_COMPLIANCE_MULTI_FRAMEWORK_ENABLED;
    delete process.env.NEXT_PUBLIC_COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED;
    delete process.env.NEXT_PUBLIC_COMPLIANCE_AGENT_ENABLED;
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it('defaults to the current SOC 2 readiness runtime labels', () => {
    const { complianceFeatureFlags, getComplianceRuntimeLabels } = loadFeatures();

    expect(complianceFeatureFlags).toEqual({
      multiFramework: false,
      evidenceRepository: false,
      complianceAgent: false,
    });
    expect(getComplianceRuntimeLabels()).toMatchObject({
      dashboardTitle: 'SOC 2 Readiness Dashboard',
      reportsTitle: 'Trust & SOC 2 Reports',
      evidenceMetricLabel: 'Report-ready signals',
    });
  });

  it('switches labels when public rollout flags are enabled', () => {
    process.env.NEXT_PUBLIC_COMPLIANCE_MULTI_FRAMEWORK_ENABLED = 'true';
    process.env.NEXT_PUBLIC_COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED = '1';
    process.env.NEXT_PUBLIC_COMPLIANCE_AGENT_ENABLED = 'yes';

    const { complianceFeatureFlags, getComplianceRuntimeLabels } = loadFeatures();

    expect(complianceFeatureFlags).toEqual({
      multiFramework: true,
      evidenceRepository: true,
      complianceAgent: true,
    });
    expect(getComplianceRuntimeLabels()).toMatchObject({
      dashboardTitle: 'Compliance Dashboard',
      reportsTitle: 'Compliance Reports',
      evidenceMetricLabel: 'Evidence items',
    });
  });
});

