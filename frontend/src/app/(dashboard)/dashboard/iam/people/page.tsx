/**
 * IAM People Page
 * Org admin can add and manage users
 */

'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusIcon,
  UserIcon,
  MagnifyingGlassIcon,
  EllipsisHorizontalIcon,
  FunnelIcon,
  AdjustmentsHorizontalIcon,
  ArrowsUpDownIcon,
  CheckCircleIcon,
  XMarkIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import {
  getIAMUsers,
  createIAMUser,
  getAccessProfiles,
  updateIAMUser,
  bulkUserAction,
  getApps,
  getBirthrightRules,
  createBirthrightRule,
  deleteBirthrightRule,
  getLifecycleSchedule,
  setLifecycleSchedule,
  getUserTimeline,
  createAccessProfile,
} from '@/lib/api/iam-portal';
import type { UserInfo, AccessProfile, UserCreate, UserEntitlement, App, BirthrightRule, LifecycleSchedule, TimelineEntry } from '@/lib/api/iam-portal';
import UserOnboardingWizard from '@/components/iam/UserOnboardingWizard';
import { useAuth } from '@/lib/providers/AuthProvider';
import { useSearchParams } from 'next/navigation';
import { toast } from 'react-hot-toast';
import { buildEntityGraphHref } from '@/lib/security/graph-context';

type SortKey = 'name' | 'email' | 'department' | 'enabled' | 'access';
type WizardStep = 'method' | 'invite' | 'bulk' | 'review';

export default function PeoplePage() {
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [showOnboardingWizard, setShowOnboardingWizard] = useState(false);
  const [showTenantSetup, setShowTenantSetup] = useState(false);
  const [setupBusy, setSetupBusy] = useState(false);
  const [setupMessage, setSetupMessage] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState<string>('all');
  const [teamFilter, setTeamFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'disabled'>('all');
  const [privilegedFilter, setPrivilegedFilter] = useState<'all' | 'privileged' | 'standard'>('all');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [birthrightDrawerOpen, setBirthrightDrawerOpen] = useState(false);
  const [detailUser, setDetailUser] = useState<UserInfo | null>(null);
  const [detailTab, setDetailTab] = useState<'profile' | 'apps'>('profile');
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>({
    name: true,
    email: true,
    department: true,
    access: true,
    status: true,
    privileged: true,
  });
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: 'asc' | 'desc' }>({
    key: 'name',
    direction: 'asc',
  });
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [columnMenuOpen, setColumnMenuOpen] = useState(false);
  const { isAuthenticated, tenantId } = useAuth();
  const searchParams = useSearchParams();
  const [onboardingStep, setOnboardingStep] = useState<WizardStep>('method');
  
  const queryClient = useQueryClient();
  const [bulkMessage, setBulkMessage] = useState<string | null>(null);
  const [initialQueryApplied, setInitialQueryApplied] = useState(false);
  const [ruleAttribute, setRuleAttribute] = useState<'department' | 'team' | 'location' | 'manager_id' | 'employee_type'>('department');
  const [ruleValue, setRuleValue] = useState('');
  const [ruleProfileId, setRuleProfileId] = useState('');
  const [ruleError, setRuleError] = useState<string | null>(null);
  const [lifecycleSchedule, setLifecycleScheduleState] = useState<LifecycleSchedule | null>(null);
  const [lifecycleLoading, setLifecycleLoading] = useState(false);
  const [lifecycleMessage, setLifecycleMessage] = useState<string | null>(null);
  const [offboardChecks, setOffboardChecks] = useState({
    access: false,
    devices: false,
    handoff: false,
  });
  const [timelineEvents, setTimelineEvents] = useState<TimelineEntry[]>([]);
  const [timelineMessage, setTimelineMessage] = useState<string | null>(null);
  
  // Fetch users
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['iam-users', departmentFilter, teamFilter, privilegedFilter],
    queryFn: () =>
      getIAMUsers({
        department: departmentFilter === 'all' ? undefined : departmentFilter,
        team: teamFilter === 'all' ? undefined : teamFilter,
        privileged: privilegedFilter === 'all' ? undefined : privilegedFilter === 'privileged',
      }),
  });

  const departmentChips = useMemo(() => {
    const uniques = new Set<string>();
    users.forEach((u) => {
      if (u.department) uniques.add(u.department);
    });
    return Array.from(uniques);
  }, [users]);

  // Fetch access profiles
  const { data: profiles = [] } = useQuery({
    queryKey: ['iam-access-profiles'],
    queryFn: getAccessProfiles,
  });

  const { data: apps = [] } = useQuery({
    queryKey: ['iam-apps'],
    queryFn: getApps,
  });

  const { data: birthrightRules = [], isLoading: isLoadingRules } = useQuery({
    queryKey: ['birthright-rules'],
    queryFn: getBirthrightRules,
  });

  const bulkActionMutation = useMutation({
    mutationFn: bulkUserAction,
    onSuccess: (data) => {
      setBulkMessage(`${data.updated} users updated via ${data.action}`);
      queryClient.invalidateQueries({ queryKey: ['iam-users'] });
    },
  });

  const rowUpdateMutation = useMutation({
    mutationFn: ({ userId, updates }: { userId: string; updates: Partial<UserInfo> }) =>
      updateIAMUser(userId, updates as Partial<UserCreate>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['iam-users'] });
    },
  });

  const createRuleMutation = useMutation({
    mutationFn: (payload: { attribute_key: 'department' | 'team' | 'location' | 'manager_id' | 'employee_type'; match_value: string; access_profile_id: string; name?: string }) =>
      createBirthrightRule(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['birthright-rules'] });
      setRuleValue('');
      setRuleProfileId('');
      setRuleError(null);
    },
    onError: (err: any) => {
      setRuleError(err?.message || 'Failed to create rule');
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: (ruleId: string) => deleteBirthrightRule(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['birthright-rules'] });
    },
  });

  const createProfileMutation = useMutation({
    mutationFn: (payload: { name: string; display_name: string; description?: string; is_default?: boolean }) =>
      createAccessProfile(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['iam-access-profiles'] });
      toast.success('Default access profile created');
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Failed to create profile');
    },
  });
  const offboardNowMutation = useMutation({
    mutationFn: (userId: string) => bulkUserAction({ action: 'offboard', user_ids: [userId] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['iam-users'] });
      toast.success('Offboarding started');
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Offboard failed');
    },
  });

  const handleBulkAction = (action: 'suspend' | 'offboard' | 'privileged') => {
    const ids = Array.from(selectedUsers);
    if (ids.length === 0) return;
    if (action === 'offboard') {
      const confirmed = window.confirm(`Offboard ${ids.length} user(s)? This disables accounts and revokes entitlements.`);
      if (!confirmed) return;
    }
    bulkActionMutation.mutate({
      action: action === 'privileged' ? 'mark_privileged' : action,
      user_ids: ids,
    });
  };

  // Create user mutation
  const createUserMutation = useMutation({
    mutationFn: createIAMUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['iam-users'] });
      setShowAddUserModal(false);
    },
  });
  
  // Derive departments for filters
  const departmentOptions = Array.from(
    new Set(users.map((u) => (u.department || '').trim()).filter(Boolean))
  ).sort((a, b) => a.localeCompare(b));

  const teamOptions = Array.from(
    new Set(users.map((u) => (u.team || '').trim()).filter(Boolean))
  ).sort((a, b) => a.localeCompare(b));

  // Filter + sort users
  const filteredUsers = users
    .filter((user) => {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        !query ||
        user.email?.toLowerCase().includes(query) ||
        user.username?.toLowerCase().includes(query) ||
        `${user.first_name || ''} ${user.last_name || ''}`.toLowerCase().includes(query);

      const matchesDept = departmentFilter === 'all' || user.department === departmentFilter;
      const matchesTeam = teamFilter === 'all' || user.team === teamFilter;
      const matchesPrivileged =
        privilegedFilter === 'all' ||
        (privilegedFilter === 'privileged' ? user.is_privileged : !user.is_privileged);
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' ? user.enabled : !user.enabled);

      return matchesSearch && matchesDept && matchesTeam && matchesPrivileged && matchesStatus;
    })
    .sort((a, b) => {
      const dir = sortConfig.direction === 'asc' ? 1 : -1;
      const key = sortConfig.key;

      if (key === 'access') {
        const aCount = a.entitlements?.length || 0;
        const bCount = b.entitlements?.length || 0;
        return (aCount - bCount) * dir;
      }

      const aVal =
        key === 'name'
          ? `${a.first_name || ''} ${a.last_name || ''}`.trim().toLowerCase() || a.username?.toLowerCase() || ''
          : (a as any)[key]?.toString().toLowerCase() || '';
      const bVal =
        key === 'name'
          ? `${b.first_name || ''} ${b.last_name || ''}`.trim().toLowerCase() || b.username?.toLowerCase() || ''
          : (b as any)[key]?.toString().toLowerCase() || '';

      return aVal.localeCompare(bVal) * dir;
    });

  const getUserDisplayName = (user: UserInfo) =>
    `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username || user.email || user.user_id;

  const getUserGraphHref = (user: UserInfo) =>
    buildEntityGraphHref({
      entityType: 'identity',
      entityId: user.user_id || user.email,
      entityLabel: getUserDisplayName(user),
      entityDomain: 'identity',
      title: `${getUserDisplayName(user)} access graph`,
      severity: user.is_privileged ? 'high' : 'medium',
      summary: user.is_privileged
        ? 'Privileged identity under access review.'
        : 'Identity access footprint for workforce review.',
      entitlementsCount: user.entitlements?.length || 0,
      sourceLabel: 'Back to People & Access',
      sourceHref: `/dashboard/iam/people?user_id=${encodeURIComponent(user.user_id || user.email)}`,
    });

  const previewMatches = useMemo(() => {
    if (!ruleValue) return [];
    const val = ruleValue.trim().toLowerCase();
    return users.filter((u) => {
      const candidate =
        ruleAttribute === 'department'
          ? u.department
          : ruleAttribute === 'team'
          ? u.team
          : ruleAttribute === 'location'
          ? (u as any).location
          : ruleAttribute === 'manager_id'
          ? (u as any).manager_id
          : (u as any).employee_type;
      return (candidate || '').toString().toLowerCase() === val;
    });
  }, [users, ruleAttribute, ruleValue]);

  const conflictingRule = useMemo(() => {
    if (!ruleValue) return null;
    const val = ruleValue.trim().toLowerCase();
    return birthrightRules.find(
      (r) => r.attribute_key?.toLowerCase() === ruleAttribute && (r.match_value || '').toLowerCase() === val
    );
  }, [birthrightRules, ruleAttribute, ruleValue]);

  const appMap = useMemo(() => {
    const map = new Map<string, App>();
    apps.forEach((app) => map.set(app.id, app));
    return map;
  }, [apps]);

  // Load lifecycle for detail user
  useEffect(() => {
    const loadLifecycle = async () => {
      if (!detailUser) return;
      try {
        setLifecycleLoading(true);
        const sched = await getLifecycleSchedule(detailUser.user_id);
        setLifecycleScheduleState(sched);
      } catch (e: any) {
        setLifecycleMessage(e?.message || 'Failed to load lifecycle');
      } finally {
        setLifecycleLoading(false);
      }
    };
    loadLifecycle();
  }, [detailUser?.user_id]);

  // Load user timeline
  useEffect(() => {
    const loadTimeline = async () => {
      if (!detailUser) {
        setTimelineEvents([]);
        return;
      }
      try {
        setTimelineMessage(null);
        const events = await getUserTimeline(detailUser.user_id);
        setTimelineEvents(events || []);
      } catch (e: any) {
        setTimelineMessage(e?.message || 'Failed to load timeline');
      }
    };
    loadTimeline();
  }, [detailUser?.user_id]);

  const userAppGroups = useMemo(() => {
    if (!detailUser?.entitlements) return [];
    const buckets: Record<string, { appId: string; entitlements: UserEntitlement[] }> = {};
    detailUser.entitlements.forEach((ent) => {
      const appId = ent.entitlement?.app_id || 'unmapped';
      if (!buckets[appId]) buckets[appId] = { appId, entitlements: [] };
      buckets[appId].entitlements.push(ent);
    });
    return Object.values(buckets);
  }, [detailUser]);

  const toggleSort = (key: SortKey) => {
    setSortConfig((prev) => {
      if (prev.key === key) {
        return { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' };
      }
      return { key, direction: 'asc' };
    });
  };

  const toggleColumn = (key: string) => {
    setVisibleColumns((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const allSelected = filteredUsers.length > 0 && filteredUsers.every((u) => selectedUsers.has(u.user_id));

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedUsers(new Set());
    } else {
      setSelectedUsers(new Set(filteredUsers.map((u) => u.user_id)));
    }
  };

  const toggleSelectUser = (id: string) => {
    setSelectedUsers((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const exportCsv = () => {
    const target = filteredUsers.filter((u) => selectedUsers.size === 0 || selectedUsers.has(u.user_id));
    if (target.length === 0) return;

    const header = ['Name', 'Email', 'Username', 'Department', 'Team', 'Privileged', 'Status', 'Access Count'];
    const rows = target.map((u) => [
      `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username,
      u.email || '',
      u.username || '',
      u.department || '',
      u.team || '',
      u.is_privileged ? 'Yes' : 'No',
      u.enabled ? 'Active' : 'Disabled',
      (u.entitlements?.length || 0).toString(),
    ]);

    const csv = [header, ...rows].map((r) => r.map((cell) => `"${(cell || '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'people.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportCsvFromApi = async () => {
    if (!isAuthenticated) return;
    try {
      const res = await fetch('/api/v1/users/export/csv', {
        credentials: 'include',
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `users_${tenantId || 'tenant'}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export CSV failed', err);
      toast.error('Export failed');
    }
  };

  // Reset tab when changing users
  useEffect(() => {
    if (detailUser) {
      setDetailTab('profile');
    }
  }, [detailUser?.user_id]);

  const setupNeeded = useMemo(() => profiles.length === 0 || birthrightRules.length === 0, [profiles.length, birthrightRules.length]);

  // Handle deep-link search params (user_id/email/principal)
  useEffect(() => {
    if (initialQueryApplied) return;
    const userIdParam = searchParams.get('user_id') || searchParams.get('principal');
    if (userIdParam) {
      setSearchQuery(userIdParam);
      setInitialQueryApplied(true);
      return;
    }
    const emailParam = searchParams.get('email');
    if (emailParam) {
      setSearchQuery(emailParam);
      setInitialQueryApplied(true);
    }
  }, [searchParams, initialQueryApplied]);
  
  return (
    <div
      className="p-6 w-full min-h-screen bg-slate-50 dark:bg-slate-950 text-text-main"
      data-testid="people-page-root"
    >
      {setupNeeded && (
        <div className="mb-4 rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-100 p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-amber-100">Complete tenant setup</p>
              <p className="text-sm text-amber-50/80">
                Create a default access profile and at least one birthright rule so joiners get day-one access automatically.
              </p>
            </div>
            <button
              onClick={() => setShowTenantSetup(true)}
              className="px-3 py-2 rounded-lg bg-surface-hover text-white text-sm hover:bg-surface-input border border-white/20"
            >
              Start setup
            </button>
          </div>
        </div>
      )}
      {/* Header / actions */}
      <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-text-main">People & Access</h1>
          <p className="text-sm text-text-muted mt-1">Search, filter, and manage users across your tenants</p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full lg:w-auto">
          <div className="relative flex-1 min-w-[240px]">
            <label htmlFor="iam-people-search" className="sr-only">
              Search people by name, email, or username
            </label>
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
            <input
              id="iam-people-search"
              type="text"
              placeholder="Search by name, email, or username..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {departmentChips.slice(0, 6).map((dept) => (
              <button
                key={dept}
                onClick={() => setDepartmentFilter(departmentFilter === dept ? 'all' : dept)}
                className={clsx(
                  'px-3 py-1 rounded-full text-sm border',
                  departmentFilter === dept
                    ? 'border-blue-600 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-200'
                    : 'border-surface-card-border text-text-muted hover:bg-surface-hover'
                )}
              >
                {dept}
              </button>
            ))}
            <button
              onClick={() => setPrivilegedFilter(privilegedFilter === 'privileged' ? 'all' : 'privileged')}
              className={clsx(
                'px-3 py-1 rounded-full text-sm border',
                privilegedFilter === 'privileged'
                  ? 'border-amber-500 bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200'
                  : 'border-surface-card-border text-text-muted hover:bg-surface-hover'
              )}
            >
              Privileged
            </button>
            {(departmentFilter !== 'all' || privilegedFilter !== 'all') && (
              <button
                onClick={() => {
                  setDepartmentFilter('all');
                  setPrivilegedFilter('all');
                }}
                className="px-2 py-1 text-xs text-text-muted hover:text-text-muted dark:text-slate-400 dark:hover:text-slate-200"
              >
                Clear chips
              </button>
            )}
          </div>
          <button
            onClick={() => setFiltersOpen((v) => !v)}
            className="flex items-center justify-center gap-2 px-3 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
          >
            <FunnelIcon className="w-5 h-5" />
            {filtersOpen ? 'Hide filters' : 'More filters'}
          </button>
          <button
            onClick={exportCsvFromApi}
            className="flex items-center justify-center gap-2 px-3 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
          >
            <ArrowsUpDownIcon className="w-5 h-5" />
            Export CSV
          </button>
          <button
            onClick={() => {
              setOnboardingStep('invite');
              setShowOnboardingWizard(true);
            }}
            className="flex items-center justify-center gap-2 px-3 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
          >
            Invite
          </button>
          <button
            onClick={() => {
              setOnboardingStep('bulk');
              setShowOnboardingWizard(true);
            }}
            className="flex items-center justify-center gap-2 px-3 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
          >
            Bulk upload
          </button>
          <button
            onClick={() => {
              setOnboardingStep('method');
              setShowOnboardingWizard(true);
            }}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            disabled={!tenantId}
            title={tenantId ? undefined : 'Tenant ID is required to add users'}
          >
            <PlusIcon className="w-5 h-5" />
            Add User
          </button>
        </div>
      </div>

      {/* Inline "Me" nav for quick personal actions */}
      <div className="mb-4">
        <div className="text-xs uppercase tracking-wide text-text-muted mb-1">Me</div>
        <div className="flex items-center gap-3">
          <a
            href="/dashboard/iam/my-profile"
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-surface-card-border bg-surface-card text-sm text-text-muted hover:border-primary/60 hover:text-primary"
          >
            My profile
            <span className="text-[11px] text-text-muted">Update name/locale/timezone</span>
          </a>
          <a
            href="/dashboard/requests"
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-surface-card-border bg-surface-card text-sm text-text-muted hover:border-primary/60 hover:text-primary"
          >
            Access requests
            <span className="text-[11px] text-text-muted">View and respond</span>
          </a>
        </div>
      </div>

      {/* Filters */}
      {filtersOpen && (
      <div className="bg-surface-card border border-surface-card-border rounded-xl shadow-sm p-4 mb-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-2">
            <div className="relative">
              <button
                onClick={() => setColumnMenuOpen((v) => !v)}
                className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-text-muted hover:bg-surface-hover"
              >
                <AdjustmentsHorizontalIcon className="w-5 h-5" />
                Columns
              </button>
              {columnMenuOpen && (
                <div className="absolute z-10 mt-2 w-48 bg-surface-card border border-surface-card-border rounded-lg shadow-lg p-3">
                  {Object.keys(visibleColumns).map((key) => (
                    <label key={key} className="flex items-center gap-2 text-sm text-text-muted py-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={visibleColumns[key]}
                        onChange={() => toggleColumn(key)}
                        className="h-4 w-4 text-blue-600 border-border rounded"
                      />
                      <span className="capitalize">{key === 'access' ? 'Access count' : key}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="all">All departments</option>
              {departmentOptions.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
            <select
              value={teamFilter}
              onChange={(e) => setTeamFilter(e.target.value)}
              className="px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="all">All teams</option>
              {teamOptions.map((team) => (
                <option key={team} value={team}>
                  {team}
                </option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="all">All statuses</option>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
            </select>
            <select
              value={privilegedFilter}
              onChange={(e) => setPrivilegedFilter(e.target.value as any)}
              className="px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="all">All access levels</option>
              <option value="privileged">Privileged only</option>
              <option value="standard">Standard only</option>
            </select>
          </div>
        </div>
        {selectedUsers.size > 0 && (
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-sm text-text-muted">
            <div className="flex items-center gap-2">
              <CheckCircleIcon className="w-5 h-5 text-blue-600" />
              <span>{selectedUsers.size} selected</span>
              {bulkMessage && <span className="text-xs text-text-muted">| {bulkMessage}</span>}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => handleBulkAction('suspend')}
                className="px-3 py-1 border border-border rounded-lg hover:bg-surface-hover"
                disabled={bulkActionMutation.isPending}
              >
                {bulkActionMutation.isPending ? 'Working...' : 'Suspend'}
              </button>
              <button
                onClick={() => handleBulkAction('offboard')}
                className="px-3 py-1 border border-border rounded-lg hover:bg-surface-hover"
                disabled={bulkActionMutation.isPending}
              >
                {bulkActionMutation.isPending ? 'Working...' : 'Offboard'}
              </button>
              <button
                onClick={() => handleBulkAction('privileged')}
                className="px-3 py-1 border border-border rounded-lg hover:bg-surface-hover"
                disabled={bulkActionMutation.isPending}
              >
                {bulkActionMutation.isPending ? 'Working...' : 'Mark privileged'}
              </button>
              <button
                onClick={() => setSelectedUsers(new Set())}
                className="px-3 py-1 text-text-muted border border-border rounded-lg hover:bg-surface-hover"
              >
                Clear
              </button>
              <button
                onClick={exportCsv}
                className="px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Export selected
              </button>
            </div>
          </div>
        )}
      </div>
    )}

    {/* Birthright management entry point */}
    <div className="mb-6 flex items-center justify-between">
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <span className="font-semibold text-text-main">People</span>
        <span className="text-text-muted">/</span>
        <button
          onClick={() => setBirthrightDrawerOpen(true)}
          className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-border text-xs font-medium hover:bg-surface-hover"
        >
          Manage birthright rules
        </button>
      </div>
    </div>

    {birthrightDrawerOpen && (
      <div className="fixed inset-0 z-40 flex">
        <div
          className="flex-1 bg-black/30 backdrop-blur-sm"
          onClick={() => setBirthrightDrawerOpen(false)}
        />
        <div className="w-full max-w-xl h-full bg-surface-card border-l border-surface-card-border shadow-2xl p-5 overflow-y-auto">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-text-main">Birthright rules</h2>
              <p className="text-sm text-text-muted">
                Auto-assign access profiles based on department, team, location, manager, or employee type.
              </p>
            </div>
            <button
              onClick={() => setBirthrightDrawerOpen(false)}
              className="text-text-muted hover:text-text-muted dark:text-slate-400 dark:hover:text-slate-200"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
          <div className="space-y-4">
            {ruleError && <div className="text-sm text-red-500">{ruleError}</div>}
            {conflictingRule && (
              <div className="text-xs text-amber-500">
                A rule already exists for this attribute/value. Update or delete the existing rule instead of adding a duplicate.
              </div>
            )}
            <div className="grid gap-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-text-muted">Attribute</label>
                  <select
                    value={ruleAttribute}
                    onChange={(e) => setRuleAttribute(e.target.value as typeof ruleAttribute)}
                    className="mt-1 w-full px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
                  >
                    <option value="department">Department</option>
                    <option value="team">Team</option>
                    <option value="location">Location</option>
                    <option value="manager_id">Manager ID</option>
                    <option value="employee_type">Employee type</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-text-muted">Match value</label>
                  <input
                    value={ruleValue}
                    onChange={(e) => setRuleValue(e.target.value)}
                    placeholder="e.g., engineering"
                    className="mt-1 w-full px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-text-muted">Access profile</label>
                <select
                  value={ruleProfileId}
                  onChange={(e) => setRuleProfileId(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
                >
                  <option value="">Select profile</option>
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.display_name || profile.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="text-xs text-text-muted bg-surface-hover border border-dashed border-surface-card-border rounded-lg p-2">
                <div className="flex items-center justify-between">
                  <span>Preview matches</span>
                  <span className="font-semibold text-text-main">
                    {previewMatches.length} user{previewMatches.length === 1 ? '' : 's'}
                  </span>
                </div>
                {previewMatches.length > 0 && (
                  <div className="mt-1 text-[11px] text-text-muted">
                    {(previewMatches.slice(0, 3) || []).map((u) => (
                      <span key={u.user_id} className="inline-block mr-2">
                        {(u.first_name || '') + ' ' + (u.last_name || u.email)}
                      </span>
                    ))}
                    {previewMatches.length > 3 && <span>+{previewMatches.length - 3} more…</span>}
                  </div>
                )}
              </div>
              <div className="flex justify-end">
                <button
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
                  onClick={() => {
                    setRuleError(null);
                    if (!ruleValue || !ruleProfileId) {
                      setRuleError('Provide a match value and profile.');
                      return;
                    }
                    createRuleMutation.mutate({
                      attribute_key: ruleAttribute,
                      match_value: ruleValue.trim(),
                      access_profile_id: ruleProfileId,
                    });
                  }}
                  disabled={createRuleMutation.isPending || !!conflictingRule}
                >
                  <PlusIcon className="w-5 h-5" />
                  Add rule
                </button>
              </div>
              <div className="border border-dashed border-surface-card-border rounded-lg p-3 min-h-[140px]">
                <p className="text-xs uppercase tracking-wide text-text-muted mb-2">Rules</p>
                {isLoadingRules ? (
                  <div className="text-sm text-text-muted">Loading rules…</div>
                ) : birthrightRules.length === 0 ? (
                  <div className="text-sm text-text-muted">No rules yet. Add your first rule.</div>
                ) : (
                  <div className="space-y-2">
                    {birthrightRules.map((rule: BirthrightRule) => {
                      const profileName = profiles.find((p) => p.id === rule.access_profile_id)?.display_name || rule.access_profile_id;
                      return (
                        <div
                          key={rule.id}
                          className="flex items-center justify-between rounded-md border border-surface-card-border bg-surface-hover px-3 py-2"
                        >
                          <div>
                            <div className="text-sm text-text-main">
                              IF <span className="font-semibold">{rule.attribute_key}</span> = "
                              <span className="font-semibold">{rule.match_value}</span>" → {profileName}
                            </div>
                            {rule.name && (
                              <div className="text-xs text-text-muted">{rule.name}</div>
                            )}
                          </div>
                          <button
                            onClick={() => deleteRuleMutation.mutate(rule.id)}
                            className="text-text-muted hover:text-red-600"
                            title="Delete rule"
                          >
                            <TrashIcon className="w-5 h-5" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )}
      {/* Table */}
      <div className="bg-surface-card border border-surface-card-border rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left">
            <thead className="bg-surface-hover border-b border-surface-card-border">
              <tr>
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleSelectAll}
                    className="h-4 w-4 text-blue-600 border-border rounded"
                  />
                </th>
                {visibleColumns.name && (
                  <SortableHeader label="Name" onClick={() => toggleSort('name')} active={sortConfig.key === 'name'} direction={sortConfig.direction} />
                )}
                {visibleColumns.email && (
                  <SortableHeader label="Email" onClick={() => toggleSort('email')} active={sortConfig.key === 'email'} direction={sortConfig.direction} />
                )}
                {visibleColumns.department && (
                  <SortableHeader
                    label="Dept / Team"
                    onClick={() => toggleSort('department')}
                    active={sortConfig.key === 'department'}
                    direction={sortConfig.direction}
                  />
                )}
                {visibleColumns.access && (
                  <SortableHeader
                    label="Access"
                    onClick={() => toggleSort('access')}
                    active={sortConfig.key === 'access'}
                    direction={sortConfig.direction}
                  />
                )}
                {visibleColumns.privileged && (
                  <th className="px-4 py-3 text-sm font-medium text-text-muted">Privileged</th>
                )}
                {visibleColumns.status && (
                  <SortableHeader
                    label="Status"
                    onClick={() => toggleSort('enabled')}
                    active={sortConfig.key === 'enabled'}
                    direction={sortConfig.direction}
                  />
                )}
                <th className="px-4 py-3 text-sm font-medium text-text-muted">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-text-muted">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <p className="mt-2 text-text-muted">Loading users...</p>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-text-muted">
                    <UserIcon className="w-10 h-10 text-text-muted mx-auto mb-3" />
                    <p className="text-text-muted">No users match your filters</p>
                    {searchQuery || departmentFilter !== 'all' || statusFilter !== 'all' ? (
                      <button
                        onClick={() => {
                          setSearchQuery('');
                          setDepartmentFilter('all');
                          setStatusFilter('all');
                        }}
                        className="mt-3 inline-flex items-center gap-2 px-3 py-2 text-sm text-blue-700 dark:text-blue-200 bg-blue-50 dark:bg-blue-900/40 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-800/50"
                      >
                        <XMarkIcon className="w-4 h-4" />
                        Clear filters
                      </button>
                    ) : null}
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.user_id} className="border-b border-border-faint dark:border-slate-800 hover:bg-surface-hover">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedUsers.has(user.user_id)}
                        onChange={() => toggleSelectUser(user.user_id)}
                        className="h-4 w-4 text-blue-600 border-border rounded"
                      />
                    </td>
                    {visibleColumns.name && (
                      <td className="px-4 py-3">
                        <div className="font-medium text-text-main">{user.first_name && user.last_name ? `${user.first_name} ${user.last_name}` : user.username}</div>
                        <div className="text-xs text-text-muted">{user.username}</div>
                      </td>
                    )}
                    {visibleColumns.email && <td className="px-4 py-3 text-text-muted">{user.email}</td>}
                    {visibleColumns.department && (
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {user.department ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-700 border border-blue-100 dark:bg-blue-900/30 dark:text-blue-100 dark:border-blue-800">
                              {user.department}
                            </span>
                          ) : (
                            <span className="text-xs text-text-muted">—</span>
                          )}
                          {user.team ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-50 text-purple-700 border border-purple-100 dark:bg-purple-900/30 dark:text-purple-100 dark:border-purple-800">
                              {user.team}
                            </span>
                          ) : null}
                        </div>
                      </td>
                    )}
                    {visibleColumns.access && (
                      <td className="px-4 py-3">
                        <span className="text-sm font-medium text-text-main">{user.entitlements?.length || 0}</span>
                        <span className="ml-1 text-xs text-text-muted">access</span>
                      </td>
                    )}
                    {visibleColumns.status && (
                      <td className="px-4 py-3">
                        <span
                          className={clsx(
                            'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                            user.enabled
                              ? 'bg-green-50 text-green-700 border border-green-100 dark:bg-green-950/40 dark:text-green-200 dark:border-green-900'
                              : 'bg-red-50 text-red-700 border border-red-100 dark:bg-red-950/40 dark:text-red-200 dark:border-red-900'
                          )}
                        >
                          <span className={clsx('h-2 w-2 rounded-full mr-1.5', user.enabled ? 'bg-green-500' : 'bg-red-500')} />
                          {user.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                    )}
                    {visibleColumns.privileged && (
                      <td className="px-4 py-3">
                        {user.is_privileged ? (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-amber-50 text-amber-700 border border-amber-100">
                            ⚠️ Privileged
                          </span>
                        ) : (
                          <span className="text-xs text-text-muted">Standard</span>
                        )}
                      </td>
                    )}
                <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setDetailUser(user)}
                          className="text-blue-700 dark:text-blue-200 hover:bg-blue-50 dark:hover:bg-blue-900/40 border border-blue-100 dark:border-blue-800 px-3 py-1 rounded-lg text-sm"
                        >
                          View
                        </button>
                        <Link
                          href={getUserGraphHref(user)}
                          className="text-blue-700 dark:text-blue-200 hover:bg-blue-50 dark:hover:bg-blue-900/40 border border-blue-100 dark:border-blue-800 px-3 py-1 rounded-lg text-sm"
                        >
                          Graph
                        </Link>
                        <ActionMenu user={user} />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddUserModal && (
        <AddUserModal
          profiles={profiles}
          tenantId={tenantId || ''}
          onClose={() => setShowAddUserModal(false)}
          onSubmit={(userData) => createUserMutation.mutate(userData)}
          isLoading={createUserMutation.isPending}
        />
      )}

      {/* User Onboarding Wizard */}
      {showOnboardingWizard && (
        <UserOnboardingWizard
          onClose={() => setShowOnboardingWizard(false)}
          initialStep={onboardingStep}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['iam-users'] });
            queryClient.refetchQueries({ queryKey: ['iam-users'] });
          }}
        />
      )}

      {/* Tenant setup helper */}
      {showTenantSetup && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center">
          <div className="bg-surface-card rounded-lg p-6 max-w-2xl w-full mx-4 border border-surface-card-border shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-text-main">Tenant setup</h2>
                <p className="text-sm text-text-muted">Create a default access profile and your first birthright rule.</p>
              </div>
              <button
                onClick={() => setShowTenantSetup(false)}
                className="text-text-muted hover:text-text-muted dark:hover:text-slate-200"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-text-main">Default access profile</p>
                    <p className="text-xs text-text-muted">Baseline entitlements for all employees (employee-base).</p>
                  </div>
                  <button
                    onClick={() => {
                      setSetupBusy(true);
                      createProfileMutation.mutate(
                        { name: 'employee-base', display_name: 'Employee Base', description: 'Baseline access for employees', is_default: true },
                        {
                          onSettled: () => setSetupBusy(false),
                        }
                      );
                    }}
                    disabled={setupBusy || createProfileMutation.isPending}
                    className="px-3 py-2 rounded-lg bg-primary text-white text-sm hover:bg-primary/80 disabled:opacity-60"
                  >
                    {createProfileMutation.isPending ? 'Creating…' : 'Create profile'}
                  </button>
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-text-main">Birthright rule</p>
                    <p className="text-xs text-text-muted">Example: IF department = engineering → Employee Base</p>
                  </div>
                  <button
                    onClick={() => {
                      if (!ruleValue || !ruleProfileId) {
                        setSetupMessage('Pick an attribute value and profile.');
                        return;
                      }
                      setSetupBusy(true);
                      createRuleMutation.mutate(
                        { attribute_key: ruleAttribute, match_value: ruleValue.trim(), access_profile_id: ruleProfileId, name: 'Default birthright' },
                        { onSettled: () => setSetupBusy(false) }
                      );
                    }}
                    disabled={setupBusy || createRuleMutation.isPending || !ruleProfileId}
                    className="px-3 py-2 rounded-lg bg-primary text-white text-sm hover:bg-primary/80 disabled:opacity-60"
                  >
                    {createRuleMutation.isPending ? 'Saving…' : 'Add rule'}
                  </button>
                </div>
                <div className="mt-3 grid md:grid-cols-3 gap-3">
                  <div className="col-span-1">
                    <label className="text-xs text-text-muted">Attribute</label>
                    <select
                      value={ruleAttribute}
                      onChange={(e) => setRuleAttribute(e.target.value as any)}
                      className="w-full px-3 py-2 border border-border rounded-lg bg-surface-card text-text-main focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="department">Department</option>
                      <option value="team">Team</option>
                      <option value="location">Location</option>
                      <option value="manager_id">Manager</option>
                      <option value="employee_type">Employee Type</option>
                    </select>
                  </div>
                  <div className="col-span-1">
                    <label className="text-xs text-text-muted">Match value</label>
                    <input
                      className="w-full px-3 py-2 border border-border rounded-lg bg-surface-card text-text-main focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="e.g., engineering"
                      value={ruleValue}
                      onChange={(e) => setRuleValue(e.target.value)}
                    />
                  </div>
                  <div className="col-span-1">
                    <label className="text-xs text-text-muted">Access profile</label>
                    <select
                      value={ruleProfileId}
                      onChange={(e) => setRuleProfileId(e.target.value)}
                      className="w-full px-3 py-2 border border-border rounded-lg bg-surface-card text-text-main focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="">Select</option>
                      {profiles.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.display_name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {setupMessage && <p className="text-xs text-red-400 mt-2">{setupMessage}</p>}
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowTenantSetup(false)}
                  className="px-3 py-2 rounded-lg border border-slate-700 text-sm text-text-main hover:border-primary/70"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    setShowTenantSetup(false);
                    toast.success('Setup saved');
                  }}
                  className="px-4 py-2 rounded-lg bg-primary text-white text-sm hover:bg-primary/80"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detail Drawer */}
      {detailUser && (
        <div className="fixed inset-0 z-40 flex">
          <div className="flex-1 bg-black/40" onClick={() => setDetailUser(null)} />
          <div className="w-full max-w-md bg-surface-card shadow-2xl p-6 overflow-y-auto border-l border-surface-card-border">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-text-main">User details</h3>
                <p className="text-sm text-text-muted">Quick view of profile and access</p>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={getUserGraphHref(detailUser)}
                  className="rounded-lg border border-blue-100 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-50 dark:border-blue-800 dark:text-blue-200 dark:hover:bg-blue-900/40"
                >
                  Open graph
                </Link>
                <button onClick={() => setDetailUser(null)} className="text-text-muted hover:text-text-muted dark:hover:text-slate-200">
                  <XMarkIcon className="w-6 h-6" />
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-base font-medium text-text-main">
                  {detailUser.first_name && detailUser.last_name
                    ? `${detailUser.first_name} ${detailUser.last_name}`
                    : detailUser.username}
                </p>
                <p className="text-xs text-text-muted">{detailUser.email || detailUser.username}</p>
              </div>
              <span
                className={clsx(
                  'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                  detailUser.enabled ? 'bg-green-50 text-green-700 border border-green-100' : 'bg-red-50 text-red-700 border border-red-100'
                )}
              >
                <span className={clsx('h-2 w-2 rounded-full mr-1.5', detailUser.enabled ? 'bg-green-500' : 'bg-red-500')} />
                {detailUser.enabled ? 'Active' : 'Disabled'}
              </span>
            </div>

            <div className="border-b border-surface-card-border mb-3">
              <nav className="flex gap-4">
                {[
                  { id: 'profile', label: 'Profile' },
                  { id: 'apps', label: 'Applications & Roles' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setDetailTab(tab.id as typeof detailTab)}
                    className={clsx(
                      'pb-2 px-1 text-sm font-medium border-b-2 transition-colors',
                      detailTab === tab.id
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-text-muted hover:text-text-muted dark:hover:text-slate-200'
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            {detailTab === 'profile' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-sm text-text-muted">Department</p>
                    <p className="text-base text-text-main">{detailUser.department || '—'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Team</p>
                    <p className="text-base text-text-main">{detailUser.team || '—'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Manager</p>
                    <p className="text-base text-text-main">{detailUser.manager_id || '—'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Privileged</p>
                    {detailUser.is_privileged ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-amber-50 text-amber-700 border border-amber-100 dark:bg-amber-900/40 dark:border-amber-800 dark:text-amber-100">
                        ⚠️ Privileged
                      </span>
                    ) : (
                      <span className="text-xs text-text-muted">Standard</span>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-sm text-text-muted">Entitlements ({detailUser.entitlements?.length || 0})</p>
                  {detailUser.entitlements && detailUser.entitlements.length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {detailUser.entitlements.slice(0, 12).map((entitlement) => (
                        <span
                          key={entitlement.id}
                          className="px-2 py-1 bg-bg-alt text-text-muted dark:bg-slate-800 dark:text-slate-100 text-xs rounded border border-surface-card-border"
                        >
                          {entitlement.entitlement?.display_name || entitlement.entitlement?.name || entitlement.entitlement_id}
                        </span>
                      ))}
                      {detailUser.entitlements.length > 12 && (
                        <span className="px-2 py-1 bg-bg-alt text-text-muted dark:bg-slate-800 dark:text-slate-100 text-xs rounded border border-surface-card-border">
                          +{detailUser.entitlements.length - 12} more
                        </span>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-text-muted mt-1">No entitlements assigned</p>
                  )}
                </div>
              </div>
            )}

            {detailTab === 'apps' && (
              <div className="space-y-3">
                <p className="text-sm text-text-muted">Applications and roles assigned to this person.</p>
                {userAppGroups.length === 0 ? (
                  <div className="text-sm text-text-muted">No app assignments yet.</div>
                ) : (
                  <div className="space-y-3">
                    {userAppGroups.map((group) => {
                      const app = appMap.get(group.appId);
                      const appLabel = group.appId === 'unmapped' ? 'Entitlements (no app mapping)' : app?.display_name || group.appId;
                      const appType = app?.app_type || (app as any)?.protocol || (app?.config as any)?.protocol || (group.appId === 'unmapped' ? 'Role only' : 'Application');
                      return (
                        <div key={`${group.appId}-${group.entitlements.length}`} className="border border-surface-card-border rounded-lg p-3">
                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <div className="text-sm font-semibold text-text-main">{appLabel}</div>
                              <div className="text-xs text-text-muted">{appType}</div>
                            </div>
                            {app && (
                              <span
                                className={clsx(
                                  'px-2 py-0.5 rounded-full text-[11px] font-medium border',
                                  app.is_active
                                    ? 'border-green-200 text-green-700 bg-green-50 dark:border-green-900 dark:text-green-200 dark:bg-green-950/40'
                                    : 'border-amber-200 text-amber-700 bg-amber-50 dark:border-amber-900 dark:text-amber-200 dark:bg-amber-950/30'
                                )}
                              >
                                {app.is_active ? 'Active' : 'Draft'}
                              </span>
                            )}
                          </div>
                          <div className="mt-2 space-y-2">
                            {group.entitlements.map((ent) => {
                              const entName = ent.entitlement?.display_name || ent.entitlement?.name || ent.entitlement_id;
                              const detail = ent.entitlement?.description || 'Role assignment';
                              return (
                                <div key={ent.id || `${ent.entitlement_id}-${ent.granted_at || 'granted'}`} className="flex items-center justify-between bg-surface-hover rounded px-2 py-2">
                                  <div>
                                    <div className="text-sm font-medium text-text-main">{entName}</div>
                                    <div className="text-xs text-text-muted">
                                      {detail}
                                      {ent.granted_by ? ` • granted by ${ent.granted_by}` : ''}
                                    </div>
                                  </div>
                                  {ent.entitlement?.is_privileged && (
                                    <span className="text-[11px] px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-100">
                                      Privileged
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Lifecycle scheduling */}
            <div className="mt-6 border-t border-surface-card-border pt-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-text-main">Lifecycle schedule</p>
                {lifecycleMessage && <span className="text-xs text-red-500">{lifecycleMessage}</span>}
              </div>
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 mb-3">
                <p className="text-xs text-amber-200 mb-2 font-semibold">Ownership transfer checklist</p>
                <div className="space-y-1 text-sm text-amber-100">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={offboardChecks.access}
                      onChange={(e) => setOffboardChecks((prev) => ({ ...prev, access: e.target.checked }))}
                      className="w-4 h-4 text-amber-500 border-amber-300 rounded"
                    />
                    Access/entitlements transferred
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={offboardChecks.devices}
                      onChange={(e) => setOffboardChecks((prev) => ({ ...prev, devices: e.target.checked }))}
                      className="w-4 h-4 text-amber-500 border-amber-300 rounded"
                    />
                    Devices reassigned or recovery initiated
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={offboardChecks.handoff}
                      onChange={(e) => setOffboardChecks((prev) => ({ ...prev, handoff: e.target.checked }))}
                      className="w-4 h-4 text-amber-500 border-amber-300 rounded"
                    />
                    Manager/stakeholders notified (tickets/ownership transfer)
                  </label>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-text-muted">Activate at</label>
                  <input
                    type="datetime-local"
                    value={
                      lifecycleSchedule?.activate_at
                        ? new Date(lifecycleSchedule.activate_at).toISOString().slice(0, 16)
                        : ''
                    }
                    onChange={(e) =>
                      setLifecycleScheduleState((prev) => ({
                        ...(prev || {}),
                        activate_at: e.target.value ? new Date(e.target.value).toISOString() : null,
                      }))
                    }
                    className="mt-1 w-full px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
                    disabled={lifecycleLoading}
                  />
                </div>
                <div>
                  <label className="text-xs text-text-muted">Offboard at</label>
                  <input
                    type="datetime-local"
                    value={
                      lifecycleSchedule?.deactivate_at
                        ? new Date(lifecycleSchedule.deactivate_at).toISOString().slice(0, 16)
                        : ''
                    }
                    onChange={(e) =>
                      setLifecycleScheduleState((prev) => ({
                        ...(prev || {}),
                        deactivate_at: e.target.value ? new Date(e.target.value).toISOString() : null,
                      }))
                    }
                    className="mt-1 w-full px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:text-slate-100"
                    disabled={lifecycleLoading}
                  />
                </div>
              </div>
              <div className="flex justify-end mt-3">
                <button
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
                  disabled={lifecycleLoading || !detailUser}
                  onClick={async () => {
                    if (!detailUser) return;
                    setLifecycleMessage(null);
                    setLifecycleLoading(true);
                    try {
                      const saved = await setLifecycleSchedule(detailUser.user_id, lifecycleSchedule || {});
                      setLifecycleScheduleState(saved);
                      setLifecycleMessage('Saved');
                      queryClient.invalidateQueries({ queryKey: ['iam-users'] });
                    } catch (e: any) {
                      setLifecycleMessage(e?.message || 'Save failed');
                    } finally {
                      setLifecycleLoading(false);
                    }
                  }}
                >
                  {lifecycleLoading ? 'Saving…' : 'Save schedule'}
                </button>
                {lifecycleSchedule?.deactivate_at && (
                  <button
                    className="ml-2 px-4 py-2 rounded-lg border border-border text-sm text-text-muted hover:bg-surface-hover"
                    onClick={async () => {
                      if (!detailUser) return;
                      setLifecycleLoading(true);
                      try {
                        const cleared = await setLifecycleSchedule(detailUser.user_id, {
                          ...(lifecycleSchedule || {}),
                          deactivate_at: null,
                        });
                        setLifecycleScheduleState(cleared);
                        setLifecycleMessage('Offboarding schedule cleared');
                        queryClient.invalidateQueries({ queryKey: ['iam-users'] });
                      } catch (e: any) {
                        setLifecycleMessage(e?.message || 'Failed to clear');
                      } finally {
                        setLifecycleLoading(false);
                      }
                    }}
                  >
                    Undo scheduled offboarding
                  </button>
                )}
              </div>
              <div className="flex gap-2 mt-2 text-xs text-text-muted">
                <button
                  className="underline"
                  onClick={() => {
                    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
                    setLifecycleScheduleState((prev) => ({
                      ...(prev || {}),
                      deactivate_at: tomorrow.toISOString(),
                    }));
                  }}
                >
                  Quick set offboard for tomorrow
                </button>
                <button
                  className="underline"
                  onClick={() => {
                    const nextHour = new Date(Date.now() + 60 * 60 * 1000);
                    setLifecycleScheduleState((prev) => ({
                      ...(prev || {}),
                      deactivate_at: nextHour.toISOString(),
                    }));
                  }}
                >
                  +1 hour
                </button>
                <button
                  className="underline"
                  onClick={() => {
                    const nextWeek = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
                    setLifecycleScheduleState((prev) => ({
                      ...(prev || {}),
                      deactivate_at: nextWeek.toISOString(),
                    }));
                  }}
                >
                  +7 days grace
                </button>
                <button
                  className={clsx(
                    'underline',
                    !(offboardChecks.access && offboardChecks.devices && offboardChecks.handoff) && 'text-red-500'
                  )}
                  onClick={async () => {
                    if (!detailUser) return;
                    if (!(offboardChecks.access && offboardChecks.devices && offboardChecks.handoff)) {
                      setLifecycleMessage('Complete the checklist before offboarding now.');
                      return;
                    }
                    try {
                      await offboardNowMutation.mutateAsync(detailUser.user_id);
                      setDetailUser(null);
                    } catch (e) {
                      setLifecycleMessage('Offboard failed');
                    }
                  }}
                  disabled={offboardNowMutation.isPending}
                >
                  {offboardNowMutation.isPending ? 'Offboarding…' : 'Offboard now'}
                </button>
              </div>
            </div>

            {/* Timeline */}
            <div className="mt-6 border-t border-surface-card-border pt-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-text-main">Lifecycle timeline</p>
                {timelineMessage && <span className="text-xs text-red-500">{timelineMessage}</span>}
              </div>
              {timelineEvents.length === 0 ? (
                <div className="text-sm text-text-muted">No recent events.</div>
              ) : (
                <div className="space-y-2">
                  {timelineEvents.map((evt) => (
                    <div
                      key={`${evt.action}-${evt.created_at}-${evt.actor_user_id || ''}`}
                      className="flex items-start gap-3 border border-surface-card-border rounded-lg px-3 py-2 bg-surface-hover"
                    >
                      <div className="text-xs font-semibold text-text-main">{evt.action}</div>
                      <div className="flex-1 text-xs text-text-muted">
                        <div>{evt.actor_email || evt.actor_user_id || 'system'}</div>
                        <div className="text-[11px] text-text-muted">
                          {evt.created_at ? new Date(evt.created_at).toLocaleString() : ''}
                        </div>
                        {evt.details && Object.keys(evt.details).length > 0 && (
                          <pre className="mt-1 text-[11px] text-text-muted bg-slate-900/30 rounded p-2">
                            {JSON.stringify(evt.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SortableHeader({
  label,
  onClick,
  active,
  direction,
}: {
  label: string;
  onClick: () => void;
  active: boolean;
  direction: 'asc' | 'desc';
}) {
  return (
    <th
      scope="col"
      className="px-4 py-3 text-sm font-medium text-text-muted cursor-pointer select-none"
      onClick={onClick}
    >
      <div className="inline-flex items-center gap-1">
        <span>{label}</span>
        <ArrowsUpDownIcon
          className={clsx(
            'w-4 h-4 text-text-muted',
            active && direction === 'asc' && 'rotate-180',
            active ? 'text-text-muted' : 'text-text-muted'
          )}
        />
      </div>
    </th>
  );
}

function ActionMenu({ user }: { user: UserInfo }) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const rowUpdateMutation = useMutation({
    mutationFn: ({ updates }: { updates: Partial<UserCreate> }) => updateIAMUser(user.user_id, updates),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['iam-users'] }),
  });
  const bulkMutation = useMutation({
    mutationFn: (action: 'offboard') => bulkUserAction({ action, user_ids: [user.user_id] }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['iam-users'] }),
  });

  const copyEmail = async () => {
    if (!user.email) return;
    try {
      await navigator.clipboard.writeText(user.email);
      setOpen(false);
    } catch (e) {
      setOpen(false);
    }
  };

  const handleAction = async (action: 'suspend' | 'offboard' | 'privileged' | 'unprivileged') => {
    setOpen(false);
    try {
      if (action === 'offboard') {
        await bulkMutation.mutateAsync('offboard');
      } else if (action === 'suspend') {
        await rowUpdateMutation.mutateAsync({ updates: { enabled: false } as Partial<UserInfo> });
      } else if (action === 'privileged') {
        await rowUpdateMutation.mutateAsync({ updates: { is_privileged: true } as Partial<UserInfo> });
      } else if (action === 'unprivileged') {
        await rowUpdateMutation.mutateAsync({ updates: { is_privileged: false } as Partial<UserInfo> });
      }
    } catch (e) {
      console.error('Row action failed', e);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="p-2 rounded-lg hover:bg-surface-hover text-text-muted dark:text-slate-200"
      >
        <EllipsisHorizontalIcon className="w-5 h-5" />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-40 bg-surface-card border border-surface-card-border rounded-lg shadow-lg py-1 z-10">
          <button
            onClick={copyEmail}
            className="w-full text-left px-3 py-2 text-sm text-text-muted hover:bg-surface-hover"
          >
            Copy email
          </button>
          <button
            onClick={() => handleAction('suspend')}
            className="w-full text-left px-3 py-2 text-sm text-text-muted hover:bg-surface-hover"
          >
            Suspend
          </button>
          <button
            onClick={() => handleAction('offboard')}
            className="w-full text-left px-3 py-2 text-sm text-text-muted hover:bg-surface-hover"
          >
            Offboard
          </button>
          <button
            onClick={() => handleAction(user.is_privileged ? 'unprivileged' : 'privileged')}
            className="w-full text-left px-3 py-2 text-sm text-text-muted hover:bg-surface-hover"
          >
            {user.is_privileged ? 'Unmark privileged' : 'Mark privileged'}
          </button>
        </div>
      )}
    </div>
  );
}


function AddUserModal({
  profiles,
  tenantId,
  onClose,
  onSubmit,
  isLoading,
}: {
  profiles: AccessProfile[];
  tenantId: string;
  onClose: () => void;
  onSubmit: (userData: UserCreate) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<UserCreate>({
    username: '',
    email: '',
    tenant_id: tenantId,
    first_name: '',
    last_name: '',
    department: '',
    team: '',
    manager_id: '',
    access_profile_id: undefined,
    make_admin: false,
  });
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.tenant_id) {
      return;
    }
    onSubmit(formData);
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto border border-surface-card-border">
        <h2 className="text-xl font-bold text-text-main mb-4">Add User</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Work Email *
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value, username: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-text-main bg-surface-card dark:bg-slate-800 font-normal"
              placeholder="user@example.com"
              style={{ color: '#111827', fontWeight: 'normal' }}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                First Name
              </label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-text-main bg-surface-card dark:bg-slate-800 font-normal"
                style={{ color: '#111827', fontWeight: 'normal' }}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Last Name
              </label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-text-main bg-surface-card dark:bg-slate-800 font-normal"
                style={{ color: '#111827', fontWeight: 'normal' }}
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Department / Team
            </label>
            <select
              value={formData.department}
              onChange={(e) => setFormData({ ...formData, department: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-text-main bg-surface-card dark:bg-slate-800 font-normal"
              style={{ color: '#111827', fontWeight: 'normal' }}
            >
              <option value="">Select a department...</option>
              <option value="Engineering">Engineering</option>
              <option value="Product">Product</option>
              <option value="Sales">Sales</option>
              <option value="Marketing">Marketing</option>
              <option value="Finance">Finance</option>
              <option value="HR">HR</option>
              <option value="Operations">Operations</option>
              <option value="Security">Security</option>
              <option value="IT">IT</option>
              <option value="Legal">Legal</option>
              <option value="Customer Success">Customer Success</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Team (optional)
            </label>
            <input
              type="text"
              value={formData.team || ''}
              onChange={(e) => setFormData({ ...formData, team: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-text-main bg-surface-card dark:bg-slate-800 font-normal"
              placeholder="Platform, IAM, GRC..."
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Access Profile
            </label>
            <select
              value={formData.access_profile_id || ''}
              onChange={(e) => setFormData({ ...formData, access_profile_id: e.target.value ? e.target.value : undefined })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-text-main bg-surface-card dark:bg-slate-800 font-normal"
              style={{ color: '#111827', fontWeight: 'normal' }}
            >
              <option value="">Select a profile...</option>
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.display_name}
                </option>
              ))}
            </select>
            <p className="text-xs text-text-muted mt-1">
              Choose a profile to automatically assign access
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="make_admin"
              checked={formData.make_admin}
              onChange={(e) => setFormData({ ...formData, make_admin: e.target.checked })}
              className="w-4 h-4 text-blue-600 border-border rounded focus:ring-blue-500"
            />
            <label htmlFor="make_admin" className="text-sm text-text-muted">
              Make them an admin?
            </label>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_privileged"
              checked={formData.is_privileged || false}
              onChange={(e) => setFormData({ ...formData, is_privileged: e.target.checked })}
              className="w-4 h-4 text-amber-600 border-border rounded focus:ring-amber-500"
            />
            <label htmlFor="is_privileged" className="text-sm text-text-muted">
              Mark as privileged
            </label>
          </div>
          
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !formData.tenant_id}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Inviting...' : 'Invite User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
