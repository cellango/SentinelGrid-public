/**
 * Certificates Page
 * Manage PKI certificates (X.509/TLS certificates)
 * Note: This is separate from IAM Certifications (access reviews)
 */

'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import { certificateApi, Certificate, CertificateFilters } from '@/lib/api/certificates';
import {
  DocumentTextIcon,
  PlusIcon,
  ArrowPathIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import Link from 'next/link';

export default function CertificatesPage() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<CertificateFilters>({});
  const [showRequestModal, setShowRequestModal] = useState(false);

  const { data: certificates = [], isLoading } = useQuery({
    queryKey: ['certificates', filters],
    queryFn: async () => {
      const response = await certificateApi.listCertificates(filters);
      return response.data;
    },
    enabled: isAuthenticated,
  });

  const { data: caAuthorities = [] } = useQuery({
    queryKey: ['ca-authorities'],
    queryFn: async () => {
      const response = await certificateApi.listCAs();
      return response.data;
    },
    enabled: isAuthenticated,
  });

  const revokeMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      certificateApi.revokeCertificate(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] });
    },
  });

  const renewMutation = useMutation({
    mutationFn: (id: string) => certificateApi.renewCertificate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] });
    },
  });

  // Calculate statistics
  const stats = {
    total: certificates.length,
    active: certificates.filter((c) => c.status === 'active').length,
    expiring: certificates.filter((c) => {
      if (c.status !== 'active' || !c.expires_at) return false;
      const expiresAt = new Date(c.expires_at);
      const daysUntilExpiry = Math.ceil(
        (expiresAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      );
      return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
    }).length,
    revoked: certificates.filter((c) => c.status === 'revoked').length,
  };

  const getStatusBadge = (cert: Certificate) => {
    const statusConfig = {
      active: {
        className: 'bg-green-100 text-green-700',
        icon: CheckCircleIcon,
        label: 'Active',
      },
      revoked: {
        className: 'bg-red-100 text-red-700',
        icon: XCircleIcon,
        label: 'Revoked',
      },
      expired: {
        className: 'bg-bg-alt text-text-muted',
        icon: ClockIcon,
        label: 'Expired',
      },
    };

    const config = statusConfig[cert.status] || statusConfig.active;
    const Icon = config.icon;

    return (
      <span
        className={`px-2 py-1 text-xs font-medium rounded flex items-center gap-1 ${config.className}`}
      >
        <Icon className="w-4 h-4" />
        {config.label}
      </span>
    );
  };

  const getExpiryStatus = (expiresAt: string) => {
    const expires = new Date(expiresAt);
    const daysUntilExpiry = Math.ceil(
      (expires.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );

    if (daysUntilExpiry < 0) {
      return { label: 'Expired', className: 'text-red-600' };
    } else if (daysUntilExpiry <= 7) {
      return { label: `${daysUntilExpiry} days`, className: 'text-red-600' };
    } else if (daysUntilExpiry <= 30) {
      return { label: `${daysUntilExpiry} days`, className: 'text-yellow-600' };
    } else {
      return { label: `${daysUntilExpiry} days`, className: 'text-text-muted' };
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-slate-600 dark:text-slate-300">Loading certificates...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Certificates</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
            Manage PKI certificates for services and devices
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/dashboard/iam/certificates/enroll"
            className="flex items-center gap-2 px-4 py-2 bg-bg-alt text-text-main dark:bg-slate-800 dark:text-slate-100 rounded-lg hover:bg-surface-hover dark:hover:bg-slate-700 transition-colors border border-surface-card-border"
          >
            <ArrowPathIcon className="w-5 h-5" />
            Enrollment
          </Link>
          <button
            onClick={() => setShowRequestModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="w-5 h-5" />
            Request Certificate
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-4">
          <div className="text-sm text-slate-600 dark:text-slate-300">Total Certificates</div>
          <div className="text-2xl font-bold mt-1">{stats.total}</div>
        </div>
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-4">
          <div className="text-sm text-slate-600 dark:text-slate-300">Active</div>
          <div className="text-2xl font-bold text-green-600 mt-1">{stats.active}</div>
        </div>
        <div className="bg-surface-card border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 bg-yellow-50 dark:bg-yellow-900/30">
          <div className="text-sm text-yellow-800 dark:text-yellow-200 flex items-center gap-1">
            <ExclamationTriangleIcon className="w-4 h-4" />
            Expiring Soon
          </div>
          <div className="text-2xl font-bold text-yellow-700 dark:text-yellow-200 mt-1">{stats.expiring}</div>
        </div>
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-4">
          <div className="text-sm text-slate-600 dark:text-slate-300">Revoked</div>
          <div className="text-2xl font-bold text-red-600 mt-1">{stats.revoked}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-surface-card border border-surface-card-border rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-xs font-medium text-text-muted mb-1">
              Status
            </label>
            <select
              value={filters.status || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  status: e.target.value as any,
                })
              }
              className="px-3 py-2 border border-border rounded-lg text-sm bg-surface-card text-slate-900 dark:text-slate-100"
            >
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="revoked">Revoked</option>
              <option value="expired">Expired</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-text-muted mb-1">
              CA Authority
            </label>
            <select
              value={filters.ca_authority_id || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  ca_authority_id: e.target.value || undefined,
                })
              }
              className="px-3 py-2 border border-border rounded-lg text-sm bg-surface-card text-slate-900 dark:text-slate-100"
            >
              <option value="">All</option>
              {caAuthorities.map((ca) => (
                <option key={ca.id} value={ca.id}>
                  {ca.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-text-muted mb-1">
              Common Name
            </label>
            <input
              type="text"
              value={filters.common_name || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  common_name: e.target.value || undefined,
                })
              }
              placeholder="Search by CN..."
              className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-surface-card text-slate-900 dark:text-slate-100"
            />
          </div>
        </div>
      </div>

      {/* Certificates List */}
      {certificates.length > 0 ? (
        <div className="bg-surface-card border border-surface-card-border rounded-lg overflow-hidden shadow-sm dark:shadow-none">
          <table className="min-w-full divide-y divide-border dark:divide-slate-800">
            <thead className="bg-surface-hover/60">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Common Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Serial Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Issued
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Expires
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-text-muted uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-surface-card divide-y divide-border dark:divide-slate-800">
              {certificates.map((cert) => {
                const expiryStatus = cert.expires_at
                  ? getExpiryStatus(cert.expires_at)
                  : null;
                return (
                  <tr key={cert.id} className="hover:bg-surface-hover/70">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        href={`/dashboard/iam/certificates/${cert.id}`}
                        className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-200"
                      >
                        <DocumentTextIcon className="w-5 h-5 text-text-muted dark:text-slate-400" />
                        {cert.common_name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-text-muted font-mono">
                        {cert.serial_number.substring(0, 16)}...
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(cert)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                      {new Date(cert.issued_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {expiryStatus ? (
                        <span className={`text-sm font-medium ${expiryStatus.className}`}>
                          {expiryStatus.label}
                        </span>
                      ) : (
                        <span className="text-sm text-text-muted">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        {cert.status === 'active' && (
                          <>
                            <button
                              onClick={() => {
                                if (
                                  confirm(
                                    `Renew certificate "${cert.common_name}"?`
                                  )
                                ) {
                                  renewMutation.mutate(cert.id);
                                }
                              }}
                              disabled={renewMutation.isPending}
                              className="text-blue-600 hover:text-blue-900 disabled:opacity-50"
                              title="Renew"
                            >
                              <ArrowPathIcon className="w-5 h-5" />
                            </button>
                            <button
                              onClick={() => {
                                const reason = prompt(
                                  `Revoke certificate "${cert.common_name}"?\n\nReason (optional):`
                                );
                                if (reason !== null) {
                                  revokeMutation.mutate({
                                    id: cert.id,
                                    reason: reason || undefined,
                                  });
                                }
                              }}
                              disabled={revokeMutation.isPending}
                              className="text-red-600 hover:text-red-900 disabled:opacity-50"
                              title="Revoke"
                            >
                              <TrashIcon className="w-5 h-5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 bg-surface-card border border-surface-card-border rounded-lg">
          <DocumentTextIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">No certificates found</p>
          <button
            onClick={() => setShowRequestModal(true)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Request Your First Certificate
          </button>
        </div>
      )}

      {/* Request Certificate Modal */}
      {showRequestModal && (
        <RequestCertificateModal
          onClose={() => setShowRequestModal(false)}
          caAuthorities={caAuthorities}
        />
      )}
    </div>
  );
}

// Request Certificate Modal
function RequestCertificateModal({
  onClose,
  caAuthorities,
}: {
  onClose: () => void;
  caAuthorities: any[];
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    common_name: '',
    subject_alternative_names: [] as string[],
    certificate_type: 'private' as 'private' | 'public',
    ca_authority_id: '',
    validity_days: '90',
  });
  const [newSan, setNewSan] = useState('');

  const createMutation = useMutation({
    mutationFn: (data: any) => certificateApi.requestCertificate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] });
      onClose();
    },
  });

  const handleAddSan = () => {
    if (newSan && !formData.subject_alternative_names.includes(newSan)) {
      setFormData({
        ...formData,
        subject_alternative_names: [...formData.subject_alternative_names, newSan],
      });
      setNewSan('');
    }
  };

  const handleRemoveSan = (san: string) => {
    setFormData({
      ...formData,
      subject_alternative_names: formData.subject_alternative_names.filter(
        (s) => s !== san
      ),
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      common_name: formData.common_name,
      subject_alternative_names:
        formData.subject_alternative_names.length > 0
          ? formData.subject_alternative_names
          : undefined,
      certificate_type: formData.certificate_type,
      ca_authority_id:
        formData.ca_authority_id || undefined,
      validity_days: parseInt(formData.validity_days),
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto text-slate-900 dark:text-slate-100">
        <h2 className="text-xl font-bold mb-4">
          Request Certificate
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Certificate Type *
            </label>
            <select
              required
              value={formData.certificate_type}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  certificate_type: e.target.value as 'private' | 'public',
                })
              }
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
            >
              <option value="private">Private (EJBCA)</option>
              <option value="public">Public (Paid Certificate)</option>
            </select>
            <p className="text-xs text-text-muted mt-1">
              {formData.certificate_type === 'private'
                ? 'Issued by your private CA (EJBCA)'
                : 'Issued by a public CA (requires payment)'}
            </p>
          </div>

          {formData.certificate_type === 'private' && (
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                CA Authority
              </label>
              <select
                value={formData.ca_authority_id}
                onChange={(e) =>
                  setFormData({ ...formData, ca_authority_id: e.target.value })
                }
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              >
                <option value="">Default</option>
                {caAuthorities.map((ca) => (
                  <option key={ca.id} value={ca.id}>
                    {ca.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Common Name (CN) *
            </label>
            <input
              type="text"
              required
              value={formData.common_name}
              onChange={(e) =>
                setFormData({ ...formData, common_name: e.target.value })
              }
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              placeholder="example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Subject Alternative Names (SANs)
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={newSan}
                onChange={(e) => setNewSan(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddSan();
                  }
                }}
                className="flex-1 px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
                placeholder="www.example.com"
              />
              <button
                type="button"
                onClick={handleAddSan}
                className="px-4 py-2 bg-bg-alt text-text-main dark:bg-slate-800 dark:text-slate-100 rounded-lg hover:bg-surface-hover dark:hover:bg-slate-700 transition-colors border border-surface-card-border"
              >
                Add
              </button>
            </div>
            {formData.subject_alternative_names.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {formData.subject_alternative_names.map((san) => (
                  <span
                    key={san}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200 rounded flex items-center gap-1"
                  >
                    {san}
                    <button
                      type="button"
                      onClick={() => handleRemoveSan(san)}
                      className="hover:text-blue-900"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Validity (days)
            </label>
            <input
              type="number"
              min={1}
              max={365}
              value={formData.validity_days}
              onChange={(e) =>
                setFormData({ ...formData, validity_days: e.target.value })
              }
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
            />
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
              disabled={createMutation.isPending}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {createMutation.isPending ? 'Requesting...' : 'Request Certificate'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
