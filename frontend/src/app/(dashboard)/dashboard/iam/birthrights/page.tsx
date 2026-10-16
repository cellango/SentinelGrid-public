/**
 * Birthrights page
 * Minimal baseline access management reusing access profiles with a birthright flag.
 */

'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PlusIcon } from '@heroicons/react/24/outline';
import {
  getBirthrights,
  createBirthright,
  getEntitlements,
  type AccessProfile,
  type Entitlement,
} from '@/lib/api/iam-portal';

type ScopeOption = { value: string; label: string };

const scopeOptions: ScopeOption[] = [
  { value: 'all_users', label: 'All users' },
  { value: 'department=Engineering', label: 'Department: Engineering' },
  { value: 'department=Sales', label: 'Department: Sales' },
  { value: 'location=Remote', label: 'Location: Remote' },
];

export default function BirthrightsPage() {
  const queryClient = useQueryClient();
  const { data: birthrights = [], isLoading } = useQuery({
    queryKey: ['iam-birthrights'],
    queryFn: getBirthrights,
  });
  const { data: entitlements = [] } = useQuery({
    queryKey: ['iam-entitlements'],
    queryFn: () => getEntitlements(),
  });

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    name: '',
    description: '',
    scope: 'all_users',
    entitlement_ids: [] as string[],
  });

  // Auto-select first entitlement when modal opens to reduce friction
  useEffect(() => {
    if (showModal && entitlements.length > 0 && form.entitlement_ids.length === 0) {
      setForm((f) => ({ ...f, entitlement_ids: [entitlements[0].id] }));
    }
  }, [showModal, entitlements, form.entitlement_ids.length]);

  const createMutation = useMutation({
    mutationFn: () => createBirthright({
      name: form.name || 'birthright',
      display_name: form.name || 'Birthright',
      description: form.description,
      scope: form.scope,
      entitlement_ids: form.entitlement_ids,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['iam-birthrights'] });
      setShowModal(false);
      setForm({ name: '', description: '', scope: 'all_users', entitlement_ids: [] });
    },
  });

  const entitlementOptions = useMemo(
    () => entitlements.map((e) => ({ value: e.id, label: `${e.display_name} (${e.entitlement_type})` })),
    [entitlements]
  );

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Birthrights</h1>
          <p className="text-sm text-text-muted dark:text-text-muted mt-1">
            Baseline access bundles automatically applied to the selected population.
          </p>
        </div>
        <button
          id="create-birthright-btn"
          onClick={() => setShowModal(true)}
          className="inline-flex items-center px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
        >
          <PlusIcon className="w-4 h-4 mr-1" />
          Create birthright
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-text-muted">Loading birthrights...</div>
      ) : birthrights.length === 0 ? (
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
          <p className="text-text-muted dark:text-text-main">No birthrights configured yet.</p>
          <p className="text-sm text-text-muted dark:text-text-muted mt-1">
            Create a birthright to give everyone (or a scoped population) day-one access.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {birthrights.map((br) => (
            <BirthrightCard key={br.id} birthright={br} />
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-card border border-surface-card-border rounded-xl p-6 w-full max-w-lg shadow-2xl">
            <h2 className="text-lg font-semibold text-text-main mb-4">Create birthright</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-muted dark:text-text-main">Name</label>
                <input
                  className="mt-1 w-full rounded-md border border-border bg-surface-card px-3 py-2 text-sm"
                  placeholder="All Employees Base Access"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-muted dark:text-text-main">Description</label>
                <textarea
                  className="mt-1 w-full rounded-md border border-border bg-surface-card px-3 py-2 text-sm"
                  rows={3}
                  placeholder="Baseline access granted on day one."
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-muted dark:text-text-main">Scope</label>
                <select
                  className="mt-1 w-full rounded-md border border-border bg-surface-card px-3 py-2 text-sm"
                  value={form.scope}
                  onChange={(e) => setForm((f) => ({ ...f, scope: e.target.value }))}
                >
                  {scopeOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-text-muted mt-1">
                  Keep it simple: start with “All users” and narrow later.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-text-muted dark:text-text-main">Entitlements</label>
                <div className="mt-2 space-y-2 max-h-40 overflow-y-auto border border-surface-card-border rounded-md p-2">
                  {entitlementOptions.length === 0 ? (
                    <p className="text-sm text-text-muted">No entitlements available.</p>
                  ) : (
                    entitlementOptions.map((opt) => {
                      const checked = form.entitlement_ids.includes(opt.value);
                      return (
                        <label key={opt.value} className="flex items-center gap-2 text-sm text-text-muted dark:text-text-main">
                          <input
                            type="checkbox"
                            className="rounded border-border"
                            checked={checked}
                            onChange={() =>
                              setForm((f) => {
                                const next = checked
                                  ? f.entitlement_ids.filter((id) => id !== opt.value)
                                  : [...f.entitlement_ids, opt.value];
                                return { ...f, entitlement_ids: next };
                              })
                            }
                          />
                          <span>{opt.label}</span>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm rounded-md border border-border text-text-muted dark:text-text-main"
                disabled={createMutation.isPending}
              >
                Cancel
              </button>
              <button
                id="submit-birthright-btn"
                onClick={() => createMutation.mutate()}
                className="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function BirthrightCard({ birthright }: { birthright: AccessProfile }) {
  return (
    <div className="bg-surface-card border border-surface-card-border rounded-lg p-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-text-main">{birthright.display_name || birthright.name}</h3>
          <p className="text-sm text-text-muted dark:text-text-muted">
            Scope: {birthright.scope || 'all_users'}
          </p>
          <p className="text-sm text-text-muted dark:text-text-muted mt-1">{birthright.description || 'Baseline access bundle'}</p>
        </div>
        <div className="text-right text-sm text-text-muted dark:text-text-muted">
          <div>{new Date(birthright.updated_at || birthright.created_at).toLocaleDateString()}</div>
          <div className="text-xs mt-1">
            {birthright.entitlements?.length || 0} entitlements
          </div>
        </div>
      </div>
      {birthright.entitlements && birthright.entitlements.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {birthright.entitlements.map((ent) => (
            <span
              key={ent.id}
              className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-100"
            >
              {ent.display_name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
