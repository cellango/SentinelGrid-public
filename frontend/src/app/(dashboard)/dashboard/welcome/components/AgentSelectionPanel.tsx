/**
 * Agent Selection Panel
 * Modern UI for selecting and managing endpoint agents
 */

'use client';

import { useState, useEffect } from 'react';
import { listAgents, downloadAgentInstaller, getAgentVersions, type EndpointAgent } from '@/lib/api/agents';
import { useQuery } from '@tanstack/react-query';

interface AgentSelectionPanelProps {
  tenantId: string;
}

export default function AgentSelectionPanel({ tenantId }: AgentSelectionPanelProps) {
  const [selectedOS, setSelectedOS] = useState<string>('all');
  const [showInstallModal, setShowInstallModal] = useState(false);

  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['agents', tenantId],
    queryFn: () => listAgents(tenantId),
    enabled: !!tenantId,
  });

  const { data: versions } = useQuery({
    queryKey: ['agent-versions', tenantId],
    queryFn: () => getAgentVersions(tenantId),
    enabled: !!tenantId,
  });

  const filteredAgents = selectedOS === 'all' 
    ? agents 
    : agents.filter(agent => agent.os_type === selectedOS);

  const osTypes = ['all', 'linux', 'windows', 'macos'];
  const onlineCount = agents.filter(a => a.status === 'online').length;

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-semibold text-text-main mb-1">Endpoint Agents</h3>
          <p className="text-sm text-text-muted">
            {onlineCount} of {agents.length} agents online
          </p>
        </div>
        <button
          onClick={() => setShowInstallModal(true)}
          className="px-4 py-2 bg-gradient-to-r from-primary to-secondary text-slate-950 rounded-xl hover:brightness-110 transition-all font-medium text-sm"
        >
          + Install Agent
        </button>
      </div>

      {/* OS Filter */}
      <div className="flex gap-2 mb-4">
        {osTypes.map((os) => (
          <button
            key={os}
            onClick={() => setSelectedOS(os)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              selectedOS === os
                ? 'bg-primary/20 text-primary border border-primary/30'
                : 'bg-[rgba(15,23,42,0.9)] text-text-muted border border-primary/10 hover:border-primary/20'
            }`}
          >
            {os === 'all' ? 'All' : os.charAt(0).toUpperCase() + os.slice(1)}
          </button>
        ))}
      </div>

      {/* Agents List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
        </div>
      ) : filteredAgents.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-4">🖥️</div>
          <p className="text-text-muted mb-2">No agents found</p>
          <p className="text-sm text-text-muted">Install an agent to start monitoring your endpoints</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAgents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} tenantId={tenantId} />
          ))}
        </div>
      )}

      {/* Install Modal */}
      {showInstallModal && (
        <InstallAgentModal
          tenantId={tenantId}
          latestVersion={versions?.latest}
          onClose={() => setShowInstallModal(false)}
        />
      )}
    </div>
  );
}

function AgentCard({ agent, tenantId }: { agent: EndpointAgent; tenantId: string }) {
  const statusColors = {
    online: 'bg-green-500/20 text-green-400 border-green-500/30',
    offline: 'bg-red-500/20 text-red-400 border-red-500/30',
    degraded: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    unknown: 'bg-surface-hover0/20 text-text-muted border-border-muted',
  };

  return (
    <div className="bg-[rgba(15,23,42,0.9)] border border-primary/10 rounded-xl p-4 hover:border-primary/30 transition-all">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <span className="text-xl">
                {agent.os_type === 'linux' ? '🐧' : agent.os_type === 'windows' ? '🪟' : '🍎'}
              </span>
            </div>
            <div>
              <h4 className="font-semibold text-text-main">{agent.name || agent.server_name || 'Unnamed Agent'}</h4>
              <p className="text-xs text-text-muted">{agent.os_name} {agent.os_version}</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <span>v{agent.version}</span>
            <span>•</span>
            <span>{agent.architecture}</span>
            {agent.environment && (
              <>
                <span>•</span>
                <span className="capitalize">{agent.environment}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${statusColors[agent.status] || statusColors.unknown}`}>
            {agent.status}
          </span>
        </div>
      </div>
    </div>
  );
}

function InstallAgentModal({
  tenantId,
  latestVersion,
  onClose,
}: {
  tenantId: string;
  latestVersion?: string;
  onClose: () => void;
}) {
  const [osType, setOsType] = useState<'linux' | 'windows' | 'macos'>('linux');
  const [architecture, setArchitecture] = useState<'x86_64' | 'arm64'>('x86_64');
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      const installer = await downloadAgentInstaller(osType, architecture, tenantId);
      if (installer.download_url) {
        window.open(installer.download_url, '_blank');
      }
    } catch (error) {
      console.error('Failed to download installer:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-[rgba(15,23,42,0.95)] backdrop-blur-xl border border-primary/30 rounded-2xl p-6 max-w-md w-full">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-text-main">Install Endpoint Agent</h3>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-main transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-main mb-2">Operating System</label>
            <div className="grid grid-cols-3 gap-2">
              {(['linux', 'windows', 'macos'] as const).map((os) => (
                <button
                  key={os}
                  onClick={() => setOsType(os)}
                  className={`px-4 py-2 rounded-xl border transition-all ${
                    osType === os
                      ? 'bg-primary/20 text-primary border-primary/30'
                      : 'bg-[rgba(15,23,42,0.9)] text-text-muted border-primary/10 hover:border-primary/20'
                  }`}
                >
                  {os.charAt(0).toUpperCase() + os.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-main mb-2">Architecture</label>
            <div className="grid grid-cols-2 gap-2">
              {(['x86_64', 'arm64'] as const).map((arch) => (
                <button
                  key={arch}
                  onClick={() => setArchitecture(arch)}
                  className={`px-4 py-2 rounded-xl border transition-all ${
                    architecture === arch
                      ? 'bg-primary/20 text-primary border-primary/30'
                      : 'bg-[rgba(15,23,42,0.9)] text-text-muted border-primary/10 hover:border-primary/20'
                  }`}
                >
                  {arch}
                </button>
              ))}
            </div>
          </div>

          {latestVersion && (
            <div className="bg-primary/10 border border-primary/20 rounded-xl p-3">
              <p className="text-sm text-text-muted">
                Latest version: <span className="text-primary font-medium">v{latestVersion}</span>
              </p>
            </div>
          )}

          <div className="flex gap-2 pt-4">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-[rgba(15,23,42,0.9)] border border-primary/10 text-text-main rounded-xl hover:border-primary/20 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDownload}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-gradient-to-r from-primary to-secondary text-slate-950 rounded-xl hover:brightness-110 disabled:opacity-50 transition-all font-medium"
            >
              {loading ? 'Downloading...' : 'Download Installer'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

