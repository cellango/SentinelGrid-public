'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Agent {
  id: string;
  agent_type: 'endpoint_protection' | 'cloud_agent' | 'network_sensor';
  hostname?: string;
  ip_address?: string;
  os_type?: string;
  os_version?: string;
  agent_version?: string;
  status: 'online' | 'offline' | 'error';
  last_seen?: string;
  metadata?: Record<string, any>;
}

export default function AgentStatus() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    online: 0,
    offline: 0,
    error: 0,
  });

  useEffect(() => {
    async function loadAgents() {
      try {
        // TODO: Fetch from API
        // For now, check localStorage or mock data
        const stored = localStorage.getItem('endpoint_agents');
        if (stored) {
          const agentList = JSON.parse(stored);
          setAgents(agentList);
          
          // Calculate stats
          setStats({
            total: agentList.length,
            online: agentList.filter((a: Agent) => a.status === 'online').length,
            offline: agentList.filter((a: Agent) => a.status === 'offline').length,
            error: agentList.filter((a: Agent) => a.status === 'error').length,
          });
        }
      } catch (error) {
        console.error('Error loading agents:', error);
      } finally {
        setLoading(false);
      }
    }

    loadAgents();
  }, []);

  const getAgentTypeIcon = (type: string) => {
    switch (type) {
      case 'endpoint_protection':
        return '🛡️';
      case 'cloud_agent':
        return '☁️';
      case 'network_sensor':
        return '🌐';
      default:
        return '📡';
    }
  };

  const getAgentTypeName = (type: string) => {
    switch (type) {
      case 'endpoint_protection':
        return 'Endpoint Protection';
      case 'cloud_agent':
        return 'Cloud Agent';
      case 'network_sensor':
        return 'Network Sensor';
      default:
        return type;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'text-green-400';
      case 'offline':
        return 'text-slate-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-slate-400';
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-700 rounded w-1/4 mb-4"></div>
          <div className="h-20 bg-slate-800 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Endpoint Agents</h3>
        <button
          onClick={() => router.push('/onboarding?step=3')}
          className="text-sm text-cyan-400 hover:text-cyan-300"
        >
          {agents.length > 0 ? 'Manage' : 'Deploy'}
        </button>
      </div>

      {/* Stats */}
      {stats.total > 0 && (
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-xs text-slate-400">Total</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{stats.online}</div>
            <div className="text-xs text-slate-400">Online</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-slate-400">{stats.offline}</div>
            <div className="text-xs text-slate-400">Offline</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">{stats.error}</div>
            <div className="text-xs text-slate-400">Error</div>
          </div>
        </div>
      )}

      {agents.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-4xl mb-2">🛡️</div>
          <p className="text-sm text-slate-400 mb-4">
            No agents deployed
          </p>
          <button
            onClick={() => router.push('/onboarding?step=3')}
            className="inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Deploy Agent
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {agents.slice(0, 5).map((agent) => (
            <div
              key={agent.id}
              className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{getAgentTypeIcon(agent.agent_type)}</span>
                <div>
                  <div className="font-medium">
                    {agent.hostname || agent.ip_address || 'Unknown Host'}
                  </div>
                  <div className="text-xs text-slate-400">
                    {getAgentTypeName(agent.agent_type)}
                    {agent.agent_version && ` • v${agent.agent_version}`}
                    {agent.os_type && ` • ${agent.os_type} ${agent.os_version || ''}`}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs font-medium ${getStatusColor(agent.status)}`}>
                  {agent.status === 'online' && '● Online'}
                  {agent.status === 'offline' && '● Offline'}
                  {agent.status === 'error' && '● Error'}
                </span>
                {agent.last_seen && (
                  <span className="text-xs text-slate-500">
                    {new Date(agent.last_seen).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          ))}
          {agents.length > 5 && (
            <button
              onClick={() => router.push('/settings?tab=agents')}
              className="w-full text-sm text-cyan-400 hover:text-cyan-300 py-2"
            >
              View all {agents.length} agents →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

