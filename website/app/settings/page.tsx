'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/Header';
import CloudConnections from '@/components/dashboard/CloudConnections';
import AgentStatus from '@/components/dashboard/AgentStatus';
import GitSecurityStatus from '@/components/dashboard/GitSecurityStatus';
import StepIdP from '@/components/onboarding/StepIdP';

type Tab = 'overview' | 'idp' | 'cloud' | 'agents' | 'git' | 'profile';

export default function SettingsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'idp', label: 'Identity Provider', icon: '🔐' },
    { id: 'cloud', label: 'Cloud Accounts', icon: '☁️' },
    { id: 'agents', label: 'Agents', icon: '🛡️' },
    { id: 'git', label: 'Git Security', icon: '🔍' },
    { id: 'profile', label: 'Profile', icon: '👤' },
  ];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Settings</h1>

        {/* Tabs */}
        <div className="border-b border-slate-800 mb-6">
          <div className="flex gap-2 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                  ${
                    activeTab === tab.id
                      ? 'border-cyan-400 text-cyan-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }
                `}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6">
                <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <button
                    onClick={() => router.push('/onboarding')}
                    className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-cyan-500 transition-colors text-left"
                  >
                    <div className="text-2xl mb-2">🚀</div>
                    <div className="font-medium mb-1">Complete Onboarding</div>
                    <div className="text-sm text-slate-400">
                      Finish setting up your SentinelGrid account
                    </div>
                  </button>
                  <button
                    onClick={() => setActiveTab('cloud')}
                    className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-cyan-500 transition-colors text-left"
                  >
                    <div className="text-2xl mb-2">☁️</div>
                    <div className="font-medium mb-1">Add Cloud Account</div>
                    <div className="text-sm text-slate-400">
                      Connect AWS, Azure, or GCP
                    </div>
                  </button>
                  <button
                    onClick={() => setActiveTab('agents')}
                    className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-cyan-500 transition-colors text-left"
                  >
                    <div className="text-2xl mb-2">🛡️</div>
                    <div className="font-medium mb-1">Deploy Agents</div>
                    <div className="text-sm text-slate-400">
                      Install endpoint protection agents
                    </div>
                  </button>
                  <button
                    onClick={() => setActiveTab('git')}
                    className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-cyan-500 transition-colors text-left"
                  >
                    <div className="text-2xl mb-2">🔍</div>
                    <div className="font-medium mb-1">Connect Git</div>
                    <div className="text-sm text-slate-400">
                      Scan repositories for security issues
                    </div>
                  </button>
                </div>
              </div>

              <CloudConnections />
              <AgentStatus />
              <GitSecurityStatus />
            </div>
          )}

          {activeTab === 'idp' && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Identity Provider</h2>
              <div className="max-w-2xl">
                <StepIdP
                  onNext={() => {
                    // Refresh or show success
                    alert('Identity provider connected successfully!');
                  }}
                  onSkip={() => {}}
                />
              </div>
            </div>
          )}

          {activeTab === 'cloud' && (
            <div>
              <CloudConnections />
            </div>
          )}

          {activeTab === 'agents' && (
            <div>
              <AgentStatus />
            </div>
          )}

          {activeTab === 'git' && (
            <div>
              <GitSecurityStatus />
            </div>
          )}

          {activeTab === 'profile' && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Profile Settings</h2>
              <div className="space-y-4 max-w-md">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    defaultValue={typeof window !== 'undefined' ? localStorage.getItem('user_email') || '' : ''}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                    readOnly
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Full Name
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                    placeholder="Your name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Company
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                    placeholder="Company name"
                  />
                </div>
                <button className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors">
                  Save Changes
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

