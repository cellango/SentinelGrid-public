/**
 * My Account Page
 * Self-service portal for users to manage their own profile, password, MFA, and sessions
 */

'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams, type ReadonlyURLSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  getProfile,
  updateProfile,
  changePassword,
  requestPasswordReset,
  getSessions,
  logoutSession,
  getApps,
  type ProfileUpdate,
  type PasswordChange,
} from '@/lib/api/iam-self-service';
import {
  UserIcon,
  KeyIcon,
  DevicePhoneMobileIcon,
  Squares2X2Icon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

type Tab = 'profile' | 'security' | 'sessions' | 'apps';
const VALID_TABS: Tab[] = ['profile', 'security', 'sessions', 'apps'];

function resolveTab(searchParams: URLSearchParams | ReadonlyURLSearchParams | null): Tab {
  const requestedTab = searchParams?.get('tab');
  return requestedTab && VALID_TABS.includes(requestedTab as Tab) ? (requestedTab as Tab) : 'profile';
}

export default function MyAccountPage() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>(() => resolveTab(searchParams));
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [resetRequestMessage, setResetRequestMessage] = useState<{
    kind: 'success' | 'warning' | 'error';
    message: string;
  } | null>(null);
  const [passwordData, setPasswordData] = useState<PasswordChange>({
    current_password: '',
    new_password: '',
  });

  const { data: profile, isLoading: profileLoading, error: profileError } = useQuery({
    queryKey: ['self-profile'],
    queryFn: () => getProfile(),
    enabled: isAuthenticated,
  });

  const { data: sessions = [], isLoading: sessionsLoading, error: sessionsError } = useQuery({
    queryKey: ['self-sessions'],
    queryFn: () => getSessions(),
    enabled: isAuthenticated && activeTab === 'sessions',
  });

  const { data: apps = [], isLoading: appsLoading, error: appsError } = useQuery({
    queryKey: ['self-apps'],
    queryFn: () => getApps(),
    enabled: isAuthenticated && activeTab === 'apps',
  });

  const updateProfileMutation = useMutation({
    mutationFn: (data: ProfileUpdate) => updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['self-profile'] });
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: (data: PasswordChange) => changePassword(data),
    onSuccess: () => {
      setShowPasswordForm(false);
      setPasswordData({ current_password: '', new_password: '' });
      alert('Password changed successfully');
    },
  });

  const requestPasswordResetMutation = useMutation({
    mutationFn: () => requestPasswordReset(),
    onSuccess: (data: any) => {
      const emailSent = data?.email_sent;
      const kind = emailSent === false ? 'warning' : 'success';
      setResetRequestMessage({
        kind,
        message:
          data?.message ||
          'Password reset request submitted. If email delivery is configured, you will receive a reset email shortly.',
      });
    },
    onError: (err: any) => {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to request password reset email';
      setResetRequestMessage({ kind: 'error', message });
    },
  });

  const logoutSessionMutation = useMutation({
    mutationFn: (sessionId: string) => logoutSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['self-sessions'] });
    },
  });

  const [profileForm, setProfileForm] = useState<ProfileUpdate>({
    firstName: '',
    lastName: '',
    locale: '',
    timezone: '',
  });

  // Initialize form when profile loads
  useEffect(() => {
    if (profile) {
      setProfileForm({
        firstName: profile.firstName || '',
        lastName: profile.lastName || '',
        locale: profile.locale || '',
        timezone: profile.timezone || '',
      });
    }
  }, [profile]);

  useEffect(() => {
    setActiveTab(resolveTab(searchParams));
  }, [searchParams]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    updateProfileMutation.mutate(profileForm);
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    changePasswordMutation.mutate(passwordData);
  };

  if (profileLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-text-muted">Loading profile...</p>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'profile' as Tab, label: 'Profile', icon: UserIcon },
    { id: 'security' as Tab, label: 'Security', icon: ShieldCheckIcon },
    { id: 'sessions' as Tab, label: 'Active Sessions', icon: DevicePhoneMobileIcon },
    { id: 'apps' as Tab, label: 'Apps', icon: Squares2X2Icon },
  ];

  const securitySignals = [
    { label: 'Email verification', value: profile?.emailVerified ? 'Verified' : profile ? 'Not verified' : 'Unavailable' },
    {
      label: 'MFA enrollment',
      value: 'Use the setup flow below. Current enrollment state is not surfaced on this page yet.',
      highlight: true,
    },
    {
      label: 'Password reset email',
      value: 'Available when SMTP delivery is configured for this tenant.',
    },
    {
      label: 'Session revocation',
      value: 'Signing out from Sessions currently ends all active sessions, not just one row.',
      highlight: true,
    },
  ];

  const selectTab = (tab: Tab) => {
    setActiveTab(tab);
    const nextParams = new URLSearchParams(searchParams?.toString());
    nextParams.set('tab', tab);
    router.replace(`/dashboard/iam/my-account?${nextParams.toString()}`, { scroll: false });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto text-slate-100">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">My Account</h1>
        <p className="text-sm text-slate-300 mt-1">Manage your profile, security, and access</p>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-surface-card-border">
        <nav className="flex gap-6">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => selectTab(tab.id)}
                className={`flex items-center gap-2 pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-text-muted hover:text-text-muted'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'profile' && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Profile Information</h2>
          {profileError && (
            <div className="mb-4 rounded-lg border border-red-700 bg-red-900/30 px-4 py-3 text-sm text-red-100">
              Unable to load your profile from IAM self-service right now.
            </div>
          )}
          {!profile && !profileError && (
            <div className="mb-4 rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-3 text-sm text-slate-300">
              Profile data is unavailable for this session.
            </div>
          )}
          <form onSubmit={handleProfileSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-200 mb-1">
                  First Name
                </label>
                <input
                  type="text"
                  value={profileForm.firstName}
                  onChange={(e) => setProfileForm({ ...profileForm, firstName: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-900/60 text-slate-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-200 mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  value={profileForm.lastName}
                  onChange={(e) => setProfileForm({ ...profileForm, lastName: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-900/60 text-slate-100"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-200 mb-1">
                Email
              </label>
              <input
                type="email"
                value={profile?.email || ''}
                disabled
                className="w-full px-3 py-2 border border-slate-700 rounded-lg bg-slate-800 text-slate-400"
              />
              <p className="text-xs text-slate-400 mt-1">Email cannot be changed</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-200 mb-1">
                  Timezone
                </label>
                <select
                  value={profileForm.timezone}
                  onChange={(e) => setProfileForm({ ...profileForm, timezone: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-900/60 text-slate-100"
                >
                  <option value="">Select timezone...</option>
                  <option value="America/New_York">Eastern Time (ET)</option>
                  <option value="America/Chicago">Central Time (CT)</option>
                  <option value="America/Denver">Mountain Time (MT)</option>
                  <option value="America/Los_Angeles">Pacific Time (PT)</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-200 mb-1">
                  Language
                </label>
                <select
                  value={profileForm.locale}
                  onChange={(e) => setProfileForm({ ...profileForm, locale: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-900/60 text-slate-100"
                >
                  <option value="">Select language...</option>
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <button
                type="submit"
                disabled={updateProfileMutation.isPending || !profile}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {updateProfileMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      )}

      {activeTab === 'security' && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-6">
          <h2 className="text-lg font-semibold text-slate-100">Security Settings</h2>

          {/* Password Change */}
          <div>
            <h3 className="font-medium text-slate-100 mb-2 flex items-center gap-2">
              <KeyIcon className="w-5 h-5" />
              Password
            </h3>
            {!showPasswordForm ? (
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={() => setShowPasswordForm(true)}
                  className="px-4 py-2 border border-slate-700 text-slate-100 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  Change Password
                </button>
                <button
                  type="button"
                  data-testid="password-reset-request-btn"
                  onClick={() => {
                    setResetRequestMessage(null);
                    requestPasswordResetMutation.mutate();
                  }}
                  disabled={requestPasswordResetMutation.isPending || !isAuthenticated}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {requestPasswordResetMutation.isPending ? 'Requesting...' : 'Send reset email'}
                </button>
                <div className="text-sm text-slate-300">
                  Sends a password reset link to your email (if email delivery is configured).
                </div>
              </div>
            ) : (
              <form onSubmit={handlePasswordSubmit} className="space-y-4 max-w-md">
                <div>
                  <label className="block text-sm font-medium text-slate-200 mb-1">
                    Current Password
                  </label>
                  <input
                    type="password"
                    required
                    value={passwordData.current_password}
                    onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-900/60 text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-200 mb-1">
                    New Password
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={passwordData.new_password}
                    onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-900/60 text-slate-100"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowPasswordForm(false);
                      setPasswordData({ current_password: '', new_password: '' });
                    }}
                    className="px-4 py-2 border border-slate-700 text-slate-100 rounded-lg hover:bg-slate-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={changePasswordMutation.isPending}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {changePasswordMutation.isPending ? 'Changing...' : 'Change Password'}
                  </button>
                </div>
              </form>
            )}
            {resetRequestMessage && (
              <div
                data-testid="password-reset-request-result"
                className={`mt-4 rounded-lg border px-4 py-3 text-sm ${
                  resetRequestMessage.kind === 'success'
                    ? 'border-emerald-700 bg-emerald-900/30 text-emerald-100'
                    : resetRequestMessage.kind === 'warning'
                      ? 'border-amber-700 bg-amber-900/30 text-amber-100'
                      : 'border-red-700 bg-red-900/30 text-red-100'
                }`}
              >
                {resetRequestMessage.message}
              </div>
            )}
          </div>

          {/* MFA Management */}
          <div>
            <h3 className="font-medium text-slate-100 mb-2">Multi-Factor Authentication</h3>
            <p className="text-sm text-slate-300 mb-4">
              Add an extra layer of security to your account
            </p>
            <button
              onClick={() => {
                router.push('/dashboard/iam/my-account?tab=security&mfa=setup');
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Set Up MFA
            </button>
          </div>
          {/* Signals */}
          <div className="grid grid-cols-2 gap-4">
            {securitySignals.map((sig) => (
              <div
                key={sig.label}
                className={`p-4 rounded-lg border ${
                  sig.highlight ? 'border-amber-700 bg-amber-900/30' : 'border-slate-800 bg-slate-900/60'
                }`}
              >
                <div className="text-sm font-medium text-slate-100">{sig.label}</div>
                <div className="text-sm text-slate-200 mt-1">{sig.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'sessions' && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Active Sessions</h2>
              <p className="mt-1 text-sm text-slate-300">
                Session visibility is live. Ending sessions here currently signs you out everywhere because targeted
                session revocation is not wired yet.
              </p>
            </div>
            {sessions.length > 0 && (
              <button
                onClick={() => logoutSessionMutation.mutate(sessions[0].id)}
                disabled={logoutSessionMutation.isPending}
                className="px-4 py-2 text-sm border border-red-800 text-red-200 rounded-lg hover:bg-red-950/40 transition-colors disabled:opacity-50"
              >
                {logoutSessionMutation.isPending ? 'Signing Out...' : 'Sign Out All Sessions'}
              </button>
            )}
          </div>
          {sessionsError ? (
            <div className="rounded-lg border border-red-700 bg-red-900/30 px-4 py-3 text-sm text-red-100">
              Unable to load active sessions right now.
            </div>
          ) : sessionsLoading ? (
            <div className="text-center py-6">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-slate-300">Loading sessions...</p>
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-slate-300">No active sessions</p>
          ) : (
            <div className="space-y-4">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className="p-4 border border-slate-800 rounded-lg bg-slate-900/70"
                >
                  <div>
                    <div className="font-medium text-slate-100">{session.username}</div>
                    <div className="text-sm text-slate-300">
                      {session.ipAddress && `IP: ${session.ipAddress}`}
                      {session.lastAccess && (
                        <span className="ml-4">
                          Last access: {new Date(session.lastAccess * 1000).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'apps' && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-2">Available Apps</h2>
          <p className="mb-4 text-sm text-slate-300">
            This launcher currently lists apps exposed in your tenant realm. Per-user app filtering is not enforced on
            this page yet.
          </p>
          {appsError ? (
            <div className="rounded-lg border border-red-700 bg-red-900/30 px-4 py-3 text-sm text-red-100">
              Unable to load app launchers right now.
            </div>
          ) : appsLoading ? (
            <div className="text-center py-6">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-slate-300">Loading apps...</p>
            </div>
          ) : apps.length === 0 ? (
            <p className="text-slate-300">No apps available</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {apps.map((app) => (
                <a
                  key={app.id}
                  href={app.baseUrl || '#'}
                  className="p-4 border border-slate-800 rounded-lg hover:border-blue-500 hover:shadow-md transition-all bg-slate-900/70 text-slate-100"
                >
                  <div className="font-medium text-slate-100">{app.name}</div>
                  {app.description && (
                    <div className="text-sm text-slate-300 mt-1">{app.description}</div>
                  )}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
