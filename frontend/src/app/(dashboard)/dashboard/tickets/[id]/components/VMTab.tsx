'use client';

interface VMTabProps {
  data?: any;
  isLoading?: boolean;
}

export default function VMTab({ data, isLoading }: VMTabProps) {
  if (isLoading) {
    return (
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <div className="animate-pulse">
          <div className="h-4 bg-[rgba(148,163,184,0.1)] rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-[rgba(148,163,184,0.1)] rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!data || !data.vulnerabilities || data.vulnerabilities.length === 0) {
    return (
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <p className="text-text-muted">No vulnerability data available.</p>
      </div>
    );
  }

  const vulnerabilities = data.vulnerabilities || [];
  const remediation = data.remediation || [];
  const patches = data.patches || [];
  const workarounds = data.workarounds || [];

  const getSeverityColor = (severity?: string) => {
    const colors: Record<string, string> = {
      critical: 'bg-red-500/20 text-red-400 border-red-500/30',
      high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    };
    return colors[severity?.toLowerCase() || 'medium'] || colors.medium;
  };

  return (
    <div className="space-y-6">
      {/* Vulnerabilities */}
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <h3 className="text-lg font-semibold text-text-main mb-4">Vulnerabilities</h3>
        <div className="space-y-4">
          {vulnerabilities.map((vuln: any, idx: number) => (
            <div key={idx} className="border border-[rgba(148,163,184,0.1)] rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h4 className="font-medium text-text-main mb-1">{vuln.cve_id || vuln.title}</h4>
                  {vuln.description && (
                    <p className="text-sm text-text-muted mb-2">{vuln.description}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  {vuln.cvss_severity && (
                    <span className={`px-2 py-1 rounded text-xs border ${getSeverityColor(vuln.cvss_severity)}`}>
                      {vuln.cvss_severity.toUpperCase()}
                    </span>
                  )}
                  {vuln.exploit_available && (
                    <span className="px-2 py-1 rounded text-xs bg-red-500/20 text-red-400 border border-red-500/30">
                      Exploit Available
                    </span>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {vuln.cvss_score && (
                  <div>
                    <p className="text-text-muted">CVSS Score</p>
                    <p className="text-text-main font-medium">{vuln.cvss_score}</p>
                  </div>
                )}
                {vuln.exploit_maturity && (
                  <div>
                    <p className="text-text-muted">Exploit Maturity</p>
                    <p className="text-text-main">{vuln.exploit_maturity}</p>
                  </div>
                )}
                {vuln.patch_available !== undefined && (
                  <div>
                    <p className="text-text-muted">Patch Available</p>
                    <p className={vuln.patch_available ? 'text-green-400' : 'text-red-400'}>
                      {vuln.patch_available ? 'Yes' : 'No'}
                    </p>
                  </div>
                )}
                {vuln.affected_products && vuln.affected_products.length > 0 && (
                  <div>
                    <p className="text-text-muted">Affected Products</p>
                    <p className="text-text-main">{vuln.affected_products.length}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Remediation Steps */}
      {remediation.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Remediation Steps</h3>
          <div className="space-y-3">
            {remediation.map((step: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-medium">
                    {idx + 1}
                  </span>
                  <div className="flex-1">
                    <p className="font-medium text-text-main mb-1">
                      {step.type || 'Remediation'} - {step.priority || 'Medium'} Priority
                    </p>
                    <p className="text-sm text-text-muted">{step.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Patches */}
      {patches.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Available Patches</h3>
          <div className="space-y-2">
            {patches.map((patch: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-text-main">{patch.source || 'Vendor'}</p>
                    {patch.description && (
                      <p className="text-sm text-text-muted">{patch.description}</p>
                    )}
                  </div>
                  {patch.url && (
                    <a
                      href={patch.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1 bg-primary text-bg rounded text-sm hover:brightness-105"
                    >
                      Download
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Workarounds */}
      {workarounds.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Workarounds</h3>
          <div className="space-y-2">
            {workarounds.map((workaround: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <p className="text-sm text-text-main">{workaround.description || workaround}</p>
                {workaround.url && (
                  <a
                    href={workaround.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary text-sm hover:underline mt-1 inline-block"
                  >
                    Learn more
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

