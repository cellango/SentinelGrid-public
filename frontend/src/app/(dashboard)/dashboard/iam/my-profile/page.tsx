/**
 * My Profile (Self-Service)
 * Allows the current user to view/update profile fields via /api/v1/self/profile.
 */

'use client';

import { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';
import { useAuth } from '@/lib/providers/AuthProvider';

type Profile = {
  id: string;
  username: string;
  email?: string;
  firstName?: string;
  lastName?: string;
  locale?: string;
  timezone?: string;
  emailVerified: boolean;
};

export default function MyProfilePage() {
  const { isAuthenticated, user } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const loadProfile = async () => {
      if (!isAuthenticated) return;
      setLoading(true);
      try {
        const res = await fetch('/api/v1/self/profile', {
          cache: 'no-store',
          credentials: 'include',
        });
        const data = await res.json();
        setProfile(data);
      } catch (err) {
        console.error(err);
        toast.error('Failed to load profile');
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, [isAuthenticated]);

  const handleSave = async () => {
    if (!isAuthenticated || !profile) return;
    setSaving(true);
    try {
      const res = await fetch('/api/v1/self/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          firstName: profile.firstName,
          lastName: profile.lastName,
          locale: profile.locale,
          timezone: profile.timezone,
        }),
      });
      if (!res.ok) throw new Error('Save failed');
      const data = await res.json();
      setProfile(data);
      toast.success('Profile updated');
    } catch (err) {
      console.error(err);
      toast.error('Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <p className="text-sm uppercase tracking-wide text-text-muted">Self-Service</p>
          <h1 className="text-2xl font-semibold">My Profile</h1>
          <p className="text-sm text-text-muted">
            Update your profile details. Changes apply to your login identity across the tenant.
          </p>
        </div>

        {loading ? (
          <div className="text-sm text-text-muted">Loading profile…</div>
        ) : profile ? (
          <div className="space-y-4 bg-surface-card rounded-xl border border-slate-200 dark:border-slate-800 p-5">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-text-muted">Email</label>
                <div className="text-sm font-medium">{profile.email || user?.email}</div>
              </div>
              <div>
                <label className="text-xs text-text-muted">Username</label>
                <div className="text-sm font-medium">{profile.username}</div>
              </div>
              <div>
                <label className="text-xs text-text-muted">First name</label>
                <input
                  value={profile.firstName || ''}
                  onChange={(e) => setProfile({ ...profile, firstName: e.target.value })}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-surface-card"
                />
              </div>
              <div>
                <label className="text-xs text-text-muted">Last name</label>
                <input
                  value={profile.lastName || ''}
                  onChange={(e) => setProfile({ ...profile, lastName: e.target.value })}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-surface-card"
                />
              </div>
              <div>
                <label className="text-xs text-text-muted">Locale</label>
                <input
                  value={profile.locale || ''}
                  onChange={(e) => setProfile({ ...profile, locale: e.target.value })}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-surface-card"
                />
              </div>
              <div>
                <label className="text-xs text-text-muted">Timezone</label>
                <input
                  value={profile.timezone || ''}
                  onChange={(e) => setProfile({ ...profile, timezone: e.target.value })}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-surface-card"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary/80 disabled:opacity-60"
              >
                {saving ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </div>
        ) : (
          <div className="text-sm text-red-500">Unable to load profile.</div>
        )}
      </div>
    </div>
  );
}
