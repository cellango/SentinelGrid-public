'use client';

interface NetworkTabProps {
  data?: any;
  isLoading?: boolean;
}

export default function NetworkTab({ data, isLoading }: NetworkTabProps) {
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

  if (!data || (!data.ip_addresses && !data.domains && !data.connections)) {
    return (
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <p className="text-text-muted">No network data available.</p>
      </div>
    );
  }

  const ipAddresses = data.ip_addresses || [];
  const domains = data.domains || [];
  const connections = data.connections || [];
  const firewallRules = data.firewall_rules || [];

  return (
    <div className="space-y-6">
      {/* IP Addresses */}
      {ipAddresses.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">IP Addresses</h3>
          <div className="space-y-3">
            {ipAddresses.map((ip: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <p className="font-medium text-text-main font-mono">{ip.ip}</p>
                  {ip.reputation && (
                    <span className={`px-2 py-1 rounded text-xs ${
                      ip.reputation.verdict === 'malicious' ? 'bg-red-500/20 text-red-400' :
                      ip.reputation.verdict === 'suspicious' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-green-500/20 text-green-400'
                    }`}>
                      {ip.reputation.verdict || 'Unknown'}
                    </span>
                  )}
                </div>
                {ip.geolocation && (
                  <p className="text-sm text-text-muted">
                    {ip.geolocation.country || 'Unknown Location'}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Domains */}
      {domains.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Domains</h3>
          <div className="space-y-2">
            {domains.map((domain: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-text-main font-mono">{domain.domain}</p>
                  {domain.reputation && (
                    <span className={`px-2 py-1 rounded text-xs ${
                      domain.reputation.verdict === 'malicious' ? 'bg-red-500/20 text-red-400' :
                      domain.reputation.verdict === 'suspicious' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-green-500/20 text-green-400'
                    }`}>
                      {domain.reputation.verdict || 'Unknown'}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Connections */}
      {connections.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Network Connections</h3>
          <div className="space-y-2">
            {connections.map((conn: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div className="flex items-center gap-4 text-sm">
                  <span className="font-mono text-text-main">{conn.source_ip || 'N/A'}</span>
                  <span className="text-text-muted">→</span>
                  <span className="font-mono text-text-main">{conn.dest_ip || 'N/A'}</span>
                  {conn.port && (
                    <span className="text-text-muted">:{conn.port}</span>
                  )}
                  {conn.protocol && (
                    <span className="px-2 py-1 bg-primary/20 text-primary rounded text-xs">
                      {conn.protocol}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Firewall Rules */}
      {firewallRules.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Firewall Rules</h3>
          <div className="space-y-2">
            {firewallRules.map((rule: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <p className="font-medium text-text-main mb-1">{rule.name || `Rule ${idx + 1}`}</p>
                <p className="text-sm text-text-muted">{rule.description || JSON.stringify(rule)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

