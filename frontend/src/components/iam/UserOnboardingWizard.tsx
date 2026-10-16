/**
 * User Onboarding Wizard Component
 * Step-by-step wizard for adding users (invite or direct creation)
 */

'use client';

import { useState } from 'react';
import { XMarkIcon, UserPlusIcon, DocumentArrowUpIcon } from '@heroicons/react/24/outline';
import { inviteUser, bulkUploadUsers, type UserInviteRequest, type BulkUploadResponse } from '@/lib/api/iam-onboarding';
import { useAuth } from '@/lib/providers/AuthProvider';

type WizardStep = 'method' | 'invite' | 'bulk' | 'review';

interface UserOnboardingWizardProps {
  onClose: () => void;
  onSuccess: () => void;
  initialStep?: WizardStep;
}

export default function UserOnboardingWizard({
  onClose,
  onSuccess,
  initialStep = 'method',
}: UserOnboardingWizardProps) {
  const { isAuthenticated } = useAuth();
  const [step, setStep] = useState<WizardStep>(initialStep);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deviceEnabled, setDeviceEnabled] = useState(false);
  const [deviceData, setDeviceData] = useState({
    device_id: '',
    name: '',
    device_type: 'laptop',
    operating_system: '',
    os_version: '',
    trust_status: 'unknown',
    ip_address: '',
  });
  
  // Invite form state
  const [inviteData, setInviteData] = useState<UserInviteRequest>({
    email: '',
    firstName: '',
    lastName: '',
    role: '',
    send_email: true,
    expires_in_days: 7,
  });
  
  // Bulk upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<BulkUploadResponse | null>(null);

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      setError('Not authenticated');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await inviteUser(inviteData);

      if (deviceEnabled && deviceData.device_id) {
        try {
          // Best-effort device registration tied to the invite email as owner
          await fetch('/api/v1/devices/register', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              ...deviceData,
              owner_email: inviteData.email,
            }),
          });
        } catch (e) {
          // Non-blocking; invite already sent
          console.warn('Device registration failed', e);
        }
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to invite user');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkUpload = async () => {
    if (!isAuthenticated) {
      setError('Not authenticated');
      return;
    }

    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await bulkUploadUsers(selectedFile);
      setUploadResult(result);
      setStep('review');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload users');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-text-main">Add Users</h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-muted"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Step Content */}
        {step === 'method' && (
          <div className="space-y-4">
            <p className="text-text-muted mb-6">Choose how you want to add users:</p>
            
            <button
              onClick={() => setStep('invite')}
              className="w-full p-4 border-2 border-surface-card-border rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
            >
              <div className="flex items-center gap-3">
                <UserPlusIcon className="w-8 h-8 text-blue-600" />
                <div>
                  <h3 className="font-semibold text-text-main">Invite User</h3>
                  <p className="text-sm text-text-muted">Send an invitation email to a new user</p>
                </div>
              </div>
            </button>

            <button
              onClick={() => setStep('bulk')}
              className="w-full p-4 border-2 border-surface-card-border rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
            >
              <div className="flex items-center gap-3">
                <DocumentArrowUpIcon className="w-8 h-8 text-blue-600" />
                <div>
                  <h3 className="font-semibold text-text-main">Bulk Upload</h3>
                  <p className="text-sm text-text-muted">Upload a CSV file with multiple users</p>
                </div>
              </div>
            </button>
          </div>
        )}

        {step === 'invite' && (
          <form onSubmit={handleInviteSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Email Address *
              </label>
              <input
                type="email"
                required
                value={inviteData.email}
                onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="user@example.com"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">
                  First Name
                </label>
                <input
                  type="text"
                  value={inviteData.firstName}
                  onChange={(e) => setInviteData({ ...inviteData, firstName: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  value={inviteData.lastName}
                  onChange={(e) => setInviteData({ ...inviteData, lastName: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Role (Optional)
              </label>
              <select
                value={inviteData.role}
                onChange={(e) => setInviteData({ ...inviteData, role: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select a role...</option>
                <option value="SOC_ANALYST">SOC Analyst</option>
                <option value="SOC_MANAGER">SOC Manager</option>
                <option value="TENANT_ADMIN">Tenant Admin</option>
                <option value="VIEW_ONLY">View Only</option>
              </select>
            </div>

            <div className="rounded-lg border border-surface-card-border p-3 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-text-main">Assign a device (optional)</p>
                  <p className="text-xs text-text-muted">Register a laptop/desktop/mobile to this user.</p>
                </div>
                <input
                  type="checkbox"
                  className="w-4 h-4 text-blue-600 border-border rounded focus:ring-blue-500"
                  checked={deviceEnabled}
                  onChange={(e) => setDeviceEnabled(e.target.checked)}
                />
              </div>
              {deviceEnabled && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-text-muted mb-1">Device ID / Serial</label>
                    <input
                      type="text"
                      value={deviceData.device_id}
                      onChange={(e) => setDeviceData({ ...deviceData, device_id: e.target.value })}
                      className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="e.g., SG-LAPTOP-001"
                      required={deviceEnabled}
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-text-muted mb-1">Name / Model</label>
                    <input
                      type="text"
                      value={deviceData.name}
                      onChange={(e) => setDeviceData({ ...deviceData, name: e.target.value })}
                      className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="MacBook Pro 14"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-text-muted mb-1">Type</label>
                    <select
                      value={deviceData.device_type}
                      onChange={(e) => setDeviceData({ ...deviceData, device_type: e.target.value })}
                      className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="laptop">Laptop</option>
                      <option value="desktop">Desktop</option>
                      <option value="mobile">Mobile</option>
                      <option value="tablet">Tablet</option>
                      <option value="server">Server</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-text-muted mb-1">Operating System</label>
                    <input
                      type="text"
                      value={deviceData.operating_system}
                      onChange={(e) => setDeviceData({ ...deviceData, operating_system: e.target.value })}
                      className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Windows 11 / macOS 14"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-text-muted mb-1">OS Version</label>
                    <input
                      type="text"
                      value={deviceData.os_version}
                      onChange={(e) => setDeviceData({ ...deviceData, os_version: e.target.value })}
                      className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="23H2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-text-muted mb-1">IP Address (optional)</label>
                    <input
                      type="text"
                      value={deviceData.ip_address}
                      onChange={(e) => setDeviceData({ ...deviceData, ip_address: e.target.value })}
                      className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="203.0.113.10"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="send_email"
                checked={inviteData.send_email}
                onChange={(e) => setInviteData({ ...inviteData, send_email: e.target.checked })}
                className="w-4 h-4 text-blue-600 border-border rounded focus:ring-blue-500"
              />
              <label htmlFor="send_email" className="text-sm text-text-muted">
                Send invitation email
              </label>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => setStep('method')}
                className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Sending...' : 'Send Invitation'}
              </button>
            </div>
          </form>
        )}

        {step === 'bulk' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-2">
                Upload CSV File
              </label>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-text-muted mt-1">
                CSV format: email,firstName,lastName,role,enabled
              </p>
            </div>

            {selectedFile && (
              <div className="p-3 bg-surface-hover rounded-lg">
                <p className="text-sm text-text-muted">
                  Selected: <span className="font-medium">{selectedFile.name}</span>
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Size: {(selectedFile.size / 1024).toFixed(2)} KB
                </p>
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <button
                onClick={() => setStep('method')}
                className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleBulkUpload}
                disabled={!selectedFile || loading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>
        )}

        {step === 'review' && uploadResult && (
          <div className="space-y-4">
            <h3 className="font-semibold text-text-main">Upload Results</h3>
            
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 bg-surface-hover rounded-lg text-center">
                <div className="text-2xl font-bold text-text-main">{uploadResult.total_rows}</div>
                <div className="text-sm text-text-muted">Total Rows</div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-green-600">{uploadResult.successful}</div>
                <div className="text-sm text-text-muted">Successful</div>
              </div>
              <div className="p-4 bg-red-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-red-600">{uploadResult.failed}</div>
                <div className="text-sm text-text-muted">Failed</div>
              </div>
            </div>

            {uploadResult.errors.length > 0 && (
              <div className="max-h-48 overflow-y-auto">
                <h4 className="text-sm font-medium text-text-muted mb-2">Errors:</h4>
                <div className="space-y-1">
                  {uploadResult.errors.map((error, idx) => (
                    <div key={idx} className="text-xs text-red-600 p-2 bg-red-50 rounded">
                      Row {error.row} ({error.email}): {error.error}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={() => {
                onSuccess();
                onClose();
              }}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
