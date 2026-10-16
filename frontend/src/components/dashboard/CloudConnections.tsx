'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface CloudAccount {
  id: string;
  cloud_provider: 'aws' | 'azure' | 'gcp';
  account_id: string;
  account_name?: string;
  status: 'connected' | 'error' | 'testing';
  connected_at?: string;
  last_sync_at?: string;
}

export default function CloudConnections() {
  const router = useRouter();
  const [clouds, setClouds] = useState<CloudAccount[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadClouds() {
      try {
        // TODO: Fetch from API
        // For now, check localStorage or mock data
        const stored = localStorage.getItem('cloud_connections');
        if (stored) {
          setClouds(JSON.parse(stored));
        }
      } catch (error) {
        console.error('Error loading cloud connections:', error);
      } finally {
        setLoading(false);
      }
    }

    loadClouds();
  }, []);

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'aws':
        return '☁️';
      case 'azure':
        return '🔷';
      case 'gcp':
        return '🔵';
      default:
        return '☁️';
    }
  };

  const getProviderName = (provider: string) => {
    switch (provider) {
      case 'aws':
        return 'AWS';
      case 'azure':
        return 'Azure';
      case 'gcp':
        return 'GCP';
      default:
        return provider.toUpperCase();
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'text-green-400';
      case 'error':
        return 'text-red-400';
      case 'testing':
        return 'text-yellow-400';
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
        <h3 className="text-lg font-semibold">Cloud Connections</h3>
        <button
          onClick={() => router.push('/onboarding?step=2')}
          className="text-sm text-cyan-400 hover:text-cyan-300"
        >
          {clouds.length > 0 ? 'Manage' : 'Connect'}
        </button>
      </div>

      {clouds.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-4xl mb-2">☁️</div>
          <p className="text-sm text-slate-400 mb-4">
            No cloud accounts connected
          </p>
          <button
            onClick={() => router.push('/onboarding?step=2')}
            className="inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Connect Cloud Account
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {clouds.map((cloud) => (
            <div
              key={cloud.id}
              className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{getProviderIcon(cloud.cloud_provider)}</span>
                <div>
                  <div className="font-medium">
                    {getProviderName(cloud.cloud_provider)}
                    {cloud.account_name && (
                      <span className="text-slate-400 ml-2">({cloud.account_name})</span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400">
                    {cloud.account_id}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs font-medium ${getStatusColor(cloud.status)}`}>
                  {cloud.status === 'connected' && '● Connected'}
                  {cloud.status === 'error' && '● Error'}
                  {cloud.status === 'testing' && '● Testing'}
                </span>
                {cloud.last_sync_at && (
                  <span className="text-xs text-slate-500">
                    Synced {new Date(cloud.last_sync_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

