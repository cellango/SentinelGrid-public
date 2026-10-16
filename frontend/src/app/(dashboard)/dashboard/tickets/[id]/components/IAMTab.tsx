'use client';

interface IAMTabProps {
  data?: any;
  isLoading?: boolean;
}

export default function IAMTab({ data, isLoading }: IAMTabProps) {
  if (isLoading) {
    return (
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <div className="animate-pulse">
          <div className="h-4 bg-[rgba(148,163,184,0.1)] rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-[rgba(148,163,184,0.1)] rounded"></div>
            <div className="h-20 bg-[rgba(148,163,184,0.1)] rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!data || (!data.users && !data.supervisors && !data.groups)) {
    return (
      <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
        <p className="text-text-muted">No IAM data available. AI enrichment may be in progress.</p>
      </div>
    );
  }

  const users = data.users || [];
  const supervisors = data.supervisors || [];
  const groups = data.groups || [];
  const permissions = data.permissions || [];
  const accessHistory = data.access_history || [];

  return (
    <div className="space-y-6">
      {/* Users */}
      {users.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Users</h3>
          <div className="space-y-4">
            {users.map((user: any, idx: number) => (
              <div key={idx} className="border border-[rgba(148,163,184,0.1)] rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-medium text-text-main">{user.display_name || user.username}</h4>
                    <p className="text-sm text-text-muted">{user.email}</p>
                  </div>
                  {user.risk_score && (
                    <span className={`px-2 py-1 rounded text-xs ${
                      user.risk_score > 7 ? 'bg-red-500/20 text-red-400' :
                      user.risk_score > 4 ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-green-500/20 text-green-400'
                    }`}>
                      Risk: {user.risk_score}/10
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-text-muted">Department</p>
                    <p className="text-text-main">{user.department || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-text-muted">Title</p>
                    <p className="text-text-main">{user.title || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-text-muted">Status</p>
                    <p className="text-text-main">{user.status || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-text-muted">Last Login</p>
                    <p className="text-text-main">
                      {user.last_login ? new Date(user.last_login).toLocaleDateString() : 'N/A'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supervisors */}
      {supervisors.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Supervisors</h3>
          <div className="space-y-2">
            {supervisors.map((supervisor: any, idx: number) => (
              <div key={idx} className="flex items-center gap-3 p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div>
                  <p className="font-medium text-text-main">{supervisor.display_name || supervisor.username}</p>
                  <p className="text-sm text-text-muted">{supervisor.email}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Groups */}
      {groups.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Group Memberships</h3>
          <div className="flex flex-wrap gap-2">
            {groups.map((group: any, idx: number) => (
              <span
                key={idx}
                className="px-3 py-1 bg-primary/20 text-primary rounded-full text-sm border border-primary/30"
              >
                {group.name || group.id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Permissions */}
      {permissions.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Permissions</h3>
          <div className="space-y-2">
            {permissions.map((permission: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <p className="font-medium text-text-main">{permission.name || permission.id}</p>
                {permission.description && (
                  <p className="text-sm text-text-muted">{permission.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Access History */}
      {accessHistory.length > 0 && (
        <div className="bg-[rgba(15,23,42,0.5)] rounded-lg p-6 border border-[rgba(148,163,184,0.1)]">
          <h3 className="text-lg font-semibold text-text-main mb-4">Access History</h3>
          <div className="space-y-2">
            {accessHistory.map((access: any, idx: number) => (
              <div key={idx} className="p-3 border border-[rgba(148,163,184,0.1)] rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-text-main">{access.action || 'Access'}</p>
                    <p className="text-sm text-text-muted">{access.resource || 'N/A'}</p>
                  </div>
                  <p className="text-sm text-text-muted">
                    {access.timestamp ? new Date(access.timestamp).toLocaleString() : 'N/A'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

