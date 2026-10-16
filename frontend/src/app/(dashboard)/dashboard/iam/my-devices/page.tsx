/**
 * My Devices (Self-Service)
 * Tenant-aware view of devices assigned to the current user with a Lost/Stolen report flow.
 */

'use client';

import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  DevicePhoneMobileIcon,
  ComputerDesktopIcon,
  ShieldExclamationIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

// Ensure API calls always go through the current origin (avoids mixed-content when the page is served over HTTPS)
const buildUrl = (path: string, params?: URLSearchParams) => {
  const base = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
  const url = new URL(path, base);
  if (params) url.search = params.toString();
  return url.toString();
};

interface Device {
  id: string;
  tenant_id: string;
  user_id: string;
  device_id: string;
  device_name?: string;
  device_type: string;
  os?: string;
  os_version?: string;
  browser?: string;
  browser_version?: string;
  ip_address?: string;
  trust_status: 'trusted' | 'untrusted' | 'unknown' | 'revoked';
  security_posture?: any;
  last_seen: string;
  first_seen: string;
  registered_at: string;
}

async function getMyDevices(
  userId?: string
): Promise<{ items: Device[]; total: number; page: number; limit: number; pages: number }> {
  const params = new URLSearchParams({ page: '1', limit: '50' });
  if (userId) params.set('user_id', userId);
  const response = await fetch(buildUrl('/api/v1/devices', params), {
    cache: 'no-store',
    credentials: 'include',
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.detail || `Failed to load devices (${response.status})`);
  }
  return data;
}

async function reportDevice(
  deviceId: string,
  reportType: 'lost' | 'stolen',
  note: string
): Promise<Device> {
  const response = await fetch(buildUrl(`/api/v1/devices/${deviceId}/report`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ report_type: reportType, note: note || null }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.detail || `Failed to report device (${response.status})`);
  }
  return data;
}

const getDeviceIcon = (deviceType: string) => {
  switch ((deviceType || '').toLowerCase()) {
    case 'desktop':
    case 'laptop':
    case 'server':
      return ComputerDesktopIcon;
    default:
      return DevicePhoneMobileIcon;
  }
};

const trustBadgeClass = (status: string) => {
  switch (status) {
    case 'trusted':
      return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-200';
    case 'untrusted':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200';
    case 'revoked':
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-200';
    default:
      return 'bg-bg-alt text-text-muted dark:bg-slate-800 dark:text-slate-200';
  }
};

function ReportDeviceModal({
  device,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  device: Device;
  onClose: () => void;
  onSubmit: (reportType: 'lost' | 'stolen', note: string) => void;
  isSubmitting: boolean;
}) {
  const [reportType, setReportType] = useState<'lost' | 'stolen'>('lost');
  const [note, setNote] = useState('');

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div
        className="bg-surface-card rounded-lg p-6 max-w-lg w-full mx-4 border border-surface-card-border text-slate-900 dark:text-slate-100"
        data-testid="report-device-modal"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Report Lost / Stolen</h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-muted dark:hover:text-slate-200"
            aria-label="Close"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        <div className="text-sm text-slate-600 dark:text-slate-300 mb-4">
          Reporting a device will mark it as <span className="font-medium">revoked</span> and notify your admin team.
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Device</label>
            <div className="text-sm text-slate-700 dark:text-slate-200">
              {device.device_name || device.device_id}
            </div>
            {device.device_name && (
              <div className="text-xs text-slate-500 dark:text-slate-400">{device.device_id}</div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as 'lost' | 'stolen')}
              className="w-full px-3 py-2 border border-border rounded-lg bg-surface-card text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              data-testid="report-type"
            >
              <option value="lost">Lost</option>
              <option value="stolen">Stolen</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Notes (optional)</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-border rounded-lg bg-surface-card text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Anything helpful for your admin team (last known location, time, etc.)"
              data-testid="report-note"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-border text-slate-700 dark:text-slate-200 hover:bg-surface-hover"
            >
              Cancel
            </button>
            <button
              onClick={() => onSubmit(reportType, note)}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed"
              data-testid="report-submit"
            >
              {isSubmitting ? 'Reporting…' : 'Report'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MyDevicesPage() {
  const { isAuthenticated, user } = useAuth();
  const queryClient = useQueryClient();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);

  const userId = user?.id;
  const isAdmin = (user?.roles || []).includes('TENANT_ADMIN') || (user?.roles || []).includes('PLATFORM_ADMIN');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['iam-my-devices', userId || 'all'],
    queryFn: () => getMyDevices(isAdmin ? undefined : userId),
    enabled: isAuthenticated && (!!userId || isAdmin),
    retry: 1,
  });

  const reportMutation = useMutation({
    mutationFn: ({ deviceId, reportType, note }: { deviceId: string; reportType: 'lost' | 'stolen'; note: string }) =>
      reportDevice(deviceId, reportType, note),
    onSuccess: (updated, variables) => {
      queryClient.invalidateQueries({ queryKey: ['iam-my-devices'] });
      setSelectedDevice(null);
      setActionMessage(`Reported "${updated.device_name || updated.device_id}" as ${variables.reportType}.`);
    },
    onError: (e: any) => {
      setActionMessage(e?.message || 'Failed to report device');
    },
  });

  const devices = useMemo(() => data?.items || [], [data?.items]);

  return (
    <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100" data-testid="my-devices-page">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">My Devices</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
          View devices assigned to you and report a device as lost or stolen.
        </p>
      </div>

      {actionMessage && (
        <div
          className="mb-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-surface-card px-4 py-3 text-sm"
          data-testid="my-devices-message"
        >
          {actionMessage}
        </div>
      )}

      {isLoading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <p className="mt-2 text-slate-600 dark:text-slate-300">Loading your devices…</p>
        </div>
      )}

      {isError && (
        <div className="text-center py-12 bg-surface-card border border-surface-card-border rounded-lg">
          <ShieldExclamationIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-slate-700 dark:text-slate-200">Unable to load devices</p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{(error as any)?.message}</p>
        </div>
      )}

      {!isLoading && !isError && devices.length === 0 && (
        <div className="text-center py-12 bg-surface-card border border-surface-card-border rounded-lg">
          <DevicePhoneMobileIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-slate-700 dark:text-slate-200">No devices assigned to you</p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            If you were issued a company device, ask your admin to assign it to your profile.
          </p>
        </div>
      )}

      {!isLoading && !isError && devices.length > 0 && (
        <div className="bg-surface-card border border-surface-card-border rounded-lg overflow-hidden shadow-sm dark:shadow-none">
          <table className="min-w-full divide-y divide-border dark:divide-slate-800">
            <thead className="bg-surface-hover/60">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Device
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Trust
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Last Seen
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-text-muted uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-surface-card divide-y divide-border dark:divide-slate-800">
              {devices.map((device) => {
                const Icon = getDeviceIcon(device.device_type);
                return (
                  <tr key={device.id} className="hover:bg-surface-hover/70">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <Icon className="w-5 h-5 text-text-muted dark:text-slate-400" />
                        <div>
                          <div className="text-sm font-medium">{device.device_name || device.device_id}</div>
                          {device.device_name && (
                            <div className="text-xs text-text-muted">{device.device_id}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm capitalize">{device.device_type}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${trustBadgeClass(device.trust_status)}`}
                        data-testid={`trust-status-${device.device_id}`}
                      >
                        {device.trust_status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                      {device.last_seen ? new Date(device.last_seen).toLocaleString() : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <button
                        className="px-3 py-1.5 rounded-lg border border-red-200 text-red-700 hover:bg-red-50 dark:border-red-900/40 dark:text-red-200 dark:hover:bg-red-900/20 disabled:opacity-60 disabled:cursor-not-allowed"
                        onClick={() => setSelectedDevice(device)}
                        disabled={device.trust_status === 'revoked'}
                        data-testid={`report-device-${device.device_id}`}
                        title={device.trust_status === 'revoked' ? 'Already revoked' : 'Report lost or stolen'}
                      >
                        Report Lost/Stolen
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {selectedDevice && (
        <ReportDeviceModal
          device={selectedDevice}
          onClose={() => setSelectedDevice(null)}
          onSubmit={(reportType, note) =>
            reportMutation.mutate({ deviceId: selectedDevice.device_id, reportType, note })
          }
          isSubmitting={reportMutation.isPending}
        />
      )}
    </div>
  );
}
