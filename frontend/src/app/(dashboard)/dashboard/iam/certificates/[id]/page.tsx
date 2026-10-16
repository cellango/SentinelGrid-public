/**
 * Certificate Detail Page
 * View certificate details, download, and manage
 */

'use client';

import { use } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { useAuth } from '@/lib/providers/AuthProvider';
import { certificateApi, Certificate } from '@/lib/api/certificates';
import {
  DocumentTextIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { useRouter } from 'next/navigation';

export default function CertificateDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: certificate, isLoading } = useQuery({
    queryKey: ['certificate', id],
    queryFn: async () => {
      const response = await certificateApi.getCertificate(id);
      return response.data;
    },
    enabled: isAuthenticated && !!id,
  });

  const revokeMutation = useMutation({
    mutationFn: (reason?: string) => certificateApi.revokeCertificate(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificate', id] });
      queryClient.invalidateQueries({ queryKey: ['certificates'] });
    },
  });

  const renewMutation = useMutation({
    mutationFn: () => certificateApi.renewCertificate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificate', id] });
      queryClient.invalidateQueries({ queryKey: ['certificates'] });
    },
  });

  const downloadCertificate = () => {
    if (!certificate?.certificate_pem) return;
    const blob = new Blob([certificate.certificate_pem], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${certificate.common_name}.crt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadPrivateKey = () => {
    if (!certificate?.private_key_pem) return;
    const blob = new Blob([certificate.private_key_pem], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${certificate.common_name}.key`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-text-muted">Loading certificate...</p>
        </div>
      </div>
    );
  }

  if (!certificate) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <XCircleIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">Certificate not found</p>
        </div>
      </div>
    );
  }

  const getStatusBadge = () => {
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

    const config = statusConfig[certificate.status] || statusConfig.active;
    const Icon = config.icon;

    return (
      <span
        className={`px-3 py-1 text-sm font-medium rounded flex items-center gap-2 ${config.className}`}
      >
        <Icon className="w-5 h-5" />
        {config.label}
      </span>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <Breadcrumbs />
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">{certificate.common_name}</h1>
          <p className="text-sm text-text-muted mt-1">Certificate Details</p>
        </div>
        <div className="flex items-center gap-3">
          {getStatusBadge()}
          {certificate.status === 'active' && (
            <>
              <button
                onClick={() => {
                  if (confirm(`Renew certificate "${certificate.common_name}"?`)) {
                    renewMutation.mutate();
                  }
                }}
                disabled={renewMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                <ArrowPathIcon className="w-5 h-5" />
                Renew
              </button>
              <button
                onClick={() => {
                  const reason = prompt(
                    `Revoke certificate "${certificate.common_name}"?\n\nReason (optional):`
                  );
                  if (reason !== null) {
                    revokeMutation.mutate(reason || undefined);
                  }
                }}
                disabled={revokeMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                <TrashIcon className="w-5 h-5" />
                Revoke
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Certificate Information */}
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-main mb-4">
              Certificate Information
            </h2>
            <dl className="grid grid-cols-1 gap-4">
              <div>
                <dt className="text-sm font-medium text-text-muted">Common Name (CN)</dt>
                <dd className="mt-1 text-sm text-text-main">{certificate.common_name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-muted">Serial Number</dt>
                <dd className="mt-1 text-sm text-text-main font-mono">
                  {certificate.serial_number}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-muted">Status</dt>
                <dd className="mt-1">{getStatusBadge()}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-muted">Issued At</dt>
                <dd className="mt-1 text-sm text-text-main">
                  {new Date(certificate.issued_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-muted">Expires At</dt>
                <dd className="mt-1 text-sm text-text-main">
                  {new Date(certificate.expires_at).toLocaleString()}
                </dd>
              </div>
              {certificate.revoked_at && (
                <div>
                  <dt className="text-sm font-medium text-text-muted">Revoked At</dt>
                  <dd className="mt-1 text-sm text-text-main">
                    {new Date(certificate.revoked_at).toLocaleString()}
                  </dd>
                </div>
              )}
              {certificate.revocation_reason && (
                <div>
                  <dt className="text-sm font-medium text-text-muted">Revocation Reason</dt>
                  <dd className="mt-1 text-sm text-text-main">
                    {certificate.revocation_reason}
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* Certificate PEM */}
          {certificate.certificate_pem && (
            <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-text-main">
                  Certificate (PEM)
                </h2>
                <button
                  onClick={downloadCertificate}
                  className="flex items-center gap-2 px-3 py-1 text-sm text-blue-600 hover:text-blue-900"
                >
                  <ArrowDownTrayIcon className="w-4 h-4" />
                  Download
                </button>
              </div>
              <pre className="bg-surface-hover border border-surface-card-border rounded-lg p-4 text-xs font-mono overflow-x-auto">
                {certificate.certificate_pem}
              </pre>
            </div>
          )}

          {/* Private Key (if available) */}
          {certificate.private_key_pem && (
            <div className="bg-surface-card border border-red-200 rounded-lg p-6 bg-red-50">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-red-900">
                  Private Key (PEM)
                </h2>
                <button
                  onClick={downloadPrivateKey}
                  className="flex items-center gap-2 px-3 py-1 text-sm text-red-600 hover:text-red-900"
                >
                  <ArrowDownTrayIcon className="w-4 h-4" />
                  Download
                </button>
              </div>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-yellow-800">
                  <strong>Warning:</strong> Keep your private key secure. Never share it or
                  commit it to version control.
                </p>
              </div>
              <pre className="bg-surface-hover border border-surface-card-border rounded-lg p-4 text-xs font-mono overflow-x-auto">
                {certificate.private_key_pem}
              </pre>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <h3 className="text-sm font-semibold text-text-main mb-4">Quick Actions</h3>
            <div className="space-y-2">
              {certificate.certificate_pem && (
                <button
                  onClick={downloadCertificate}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
                >
                  <ArrowDownTrayIcon className="w-5 h-5" />
                  Download Certificate
                </button>
              )}
              {certificate.private_key_pem && (
                <button
                  onClick={downloadPrivateKey}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 transition-colors"
                >
                  <ArrowDownTrayIcon className="w-5 h-5" />
                  Download Private Key
                </button>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <h3 className="text-sm font-semibold text-text-main mb-4">Metadata</h3>
            <dl className="space-y-3">
              <div>
                <dt className="text-xs font-medium text-text-muted">Certificate ID</dt>
                <dd className="mt-1 text-xs text-text-main font-mono break-all">
                  {certificate.id}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-text-muted">CA Authority ID</dt>
                <dd className="mt-1 text-xs text-text-main font-mono break-all">
                  {certificate.ca_authority_id}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-text-muted">Created At</dt>
                <dd className="mt-1 text-xs text-text-main">
                  {new Date(certificate.created_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-text-muted">Updated At</dt>
                <dd className="mt-1 text-xs text-text-main">
                  {new Date(certificate.updated_at).toLocaleString()}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
