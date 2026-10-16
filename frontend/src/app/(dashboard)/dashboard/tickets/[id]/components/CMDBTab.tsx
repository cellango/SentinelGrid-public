'use client';

interface CMDBTabProps {
  data?: any;
  isLoading?: boolean;
}

export default function CMDBTab({ data, isLoading }: CMDBTabProps) {
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

  if (!data || !data.assets || data.assets.length === 0) {
    return (
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <p className="text-text-muted">No CMDB data available.</p>
      </div>
    );
  }

  const assets = data.assets || [];
  const softwareInventory = data.software_inventory || [];
  const hardwareInventory = data.hardware_inventory || [];

  return (
    <div className="space-y-6">
      {/* Assets */}
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <h3 className="text-lg font-semibold text-text-main mb-4">Assets</h3>
        <div className="space-y-4">
          {assets.map((asset: any, idx: number) => (
            <div key={idx} className="border border-[rgba(148,163,184,0.1)] rounded-lg p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-medium text-text-main mb-1">{asset.name || asset.asset_id}</h4>
                  <p className="text-sm text-text-muted">{asset.asset_type}</p>
                </div>
                {asset.compliance_status && (
                  <span className={`px-2 py-1 rounded text-xs ${
                    asset.compliance_status === 'compliant' ? 'bg-green-500/20 text-green-400' :
                    asset.compliance_status === 'non-compliant' ? 'bg-red-500/20 text-red-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {asset.compliance_status}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-text-muted">Hostname</p>
                  <p className="text-text-main">{asset.hostname || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-text-muted">IP Address</p>
                  <p className="text-text-main">{asset.ip_address || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-text-muted">Operating System</p>
                  <p className="text-text-main">{asset.operating_system || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-text-muted">Owner</p>
                  <p className="text-text-main">{asset.owner || 'N/A'}</p>
                </div>
                {asset.location && (
                  <div>
                    <p className="text-text-muted">Location</p>
                    <p className="text-text-main">{asset.location}</p>
                  </div>
                )}
                {asset.department && (
                  <div>
                    <p className="text-text-muted">Department</p>
                    <p className="text-text-main">{asset.department}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Software Inventory */}
      {softwareInventory.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Software Inventory</h3>
          <div className="space-y-2">
            {softwareInventory.map((software: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-text-main">{software.name || software.product}</p>
                    {software.version && (
                      <p className="text-sm text-text-muted">Version: {software.version}</p>
                    )}
                  </div>
                  {software.vendor && (
                    <p className="text-sm text-text-muted">{software.vendor}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hardware Inventory */}
      {hardwareInventory.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Hardware Inventory</h3>
          <div className="space-y-4">
            {hardwareInventory.map((hardware: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  {hardware.manufacturer && (
                    <div>
                      <p className="text-text-muted">Manufacturer</p>
                      <p className="text-text-main">{hardware.manufacturer}</p>
                    </div>
                  )}
                  {hardware.model && (
                    <div>
                      <p className="text-text-muted">Model</p>
                      <p className="text-text-main">{hardware.model}</p>
                    </div>
                  )}
                  {hardware.serial_number && (
                    <div>
                      <p className="text-text-muted">Serial Number</p>
                      <p className="text-text-main">{hardware.serial_number}</p>
                    </div>
                  )}
                  {hardware.specs && (
                    <div>
                      <p className="text-text-muted">Specs</p>
                      <p className="text-text-main">
                        {hardware.specs.instance_type || hardware.specs.cpu_cores || 'N/A'}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

