/**
 * Certificate Enrollment Page
 * Provides enrollment protocol information and wizards
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  certificateApi,
  ACMEDirectory,
  SCEPEndpoint,
  ESTEndpoints,
} from '@/lib/api/certificates';
import {
  DocumentTextIcon,
  ClipboardDocumentIcon,
  CheckCircleIcon,
  CodeBracketIcon,
} from '@heroicons/react/24/outline';

type ProtocolTab = 'acme' | 'scep' | 'est' | 'overview';

export default function EnrollmentPage() {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<ProtocolTab>('overview');

  const { data: protocols } = useQuery({
    queryKey: ['enrollment-protocols'],
    queryFn: async () => {
      const response = await certificateApi.listEnrollmentProtocols();
      return response.data;
    },
    enabled: isAuthenticated,
  });

  const { data: acmeDirectory } = useQuery({
    queryKey: ['acme-directory'],
    queryFn: async () => {
      const response = await certificateApi.getACMEDirectory();
      return response.data;
    },
    enabled: isAuthenticated && activeTab === 'acme',
  });

  const { data: scepEndpoint } = useQuery({
    queryKey: ['scep-endpoint'],
    queryFn: async () => {
      const response = await certificateApi.getSCEPEndpoint();
      return response.data;
    },
    enabled: isAuthenticated && activeTab === 'scep',
  });

  const { data: estEndpoints } = useQuery({
    queryKey: ['est-endpoints'],
    queryFn: async () => {
      const response = await certificateApi.getESTEndpoints();
      return response.data;
    },
    enabled: isAuthenticated && activeTab === 'est',
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-main">Certificate Enrollment</h1>
        <p className="text-sm text-text-muted mt-1">
          Automated certificate enrollment using ACME, SCEP, or EST protocols
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-surface-card-border mb-6">
        <nav className="flex gap-6">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'acme', label: 'ACME' },
            { id: 'scep', label: 'SCEP' },
            { id: 'est', label: 'EST' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as ProtocolTab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-text-muted hover:text-text-main'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-main mb-4">
              Enrollment Protocols
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {protocols?.protocols &&
                Object.entries(protocols.protocols).map(([key, protocol]) => (
                  <div
                    key={key}
                    className="border border-surface-card-border rounded-lg p-4 hover:border-blue-300 transition-colors"
                  >
                    <h3 className="font-semibold text-text-main mb-2">
                      {protocol.name}
                    </h3>
                    <p className="text-sm text-text-muted mb-3">{protocol.version}</p>
                    <div className="mb-3">
                      <p className="text-xs font-medium text-text-muted mb-1">
                        Use Cases:
                      </p>
                      <ul className="text-xs text-text-muted space-y-1">
                        {protocol.use_cases.map((useCase, idx) => (
                          <li key={idx}>• {useCase}</li>
                        ))}
                      </ul>
                    </div>
                    <button
                      onClick={() => setActiveTab(key as ProtocolTab)}
                      className="text-sm text-blue-600 hover:text-blue-900"
                    >
                      View Details →
                    </button>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* ACME Tab */}
      {activeTab === 'acme' && (
        <div className="space-y-6">
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-main mb-4">
              ACME (Automatic Certificate Management Environment)
            </h2>
            <p className="text-sm text-text-muted mb-6">
              ACME is ideal for web servers, Kubernetes clusters, and automated certificate
              renewal. Compatible with certbot, cert-manager, and acme.sh.
            </p>

            {acmeDirectory && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">
                    ACME Directory URL
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      readOnly
                      value={acmeDirectory.directory_url}
                      className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface-hover font-mono text-sm"
                    />
                    <button
                      onClick={() => copyToClipboard(acmeDirectory.directory_url)}
                      className="px-4 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-text-muted mb-1">
                      New Account URL
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        readOnly
                        value={acmeDirectory.new_account_url}
                        className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface-hover font-mono text-xs"
                      />
                      <button
                        onClick={() => copyToClipboard(acmeDirectory.new_account_url)}
                        className="px-3 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text-muted mb-1">
                      New Order URL
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        readOnly
                        value={acmeDirectory.new_order_url}
                        className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface-hover font-mono text-xs"
                      />
                      <button
                        onClick={() => copyToClipboard(acmeDirectory.new_order_url)}
                        className="px-3 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                </div>

                {/* Example Configurations */}
                <div className="mt-6 border-t border-surface-card-border pt-6">
                  <h3 className="text-sm font-semibold text-text-main mb-3">
                    Example Configurations
                  </h3>

                  <div className="space-y-4">
                    {/* certbot */}
                    <div>
                      <p className="text-sm font-medium text-text-muted mb-2">
                        certbot:
                      </p>
                      <div className="bg-bg text-text-main rounded-lg p-4 font-mono text-xs overflow-x-auto">
                        <pre>
                          {`certbot certonly \\
  --server ${acmeDirectory.directory_url} \\
  --manual \\
  --preferred-challenges http \\
  -d example.com`}
                        </pre>
                      </div>
                    </div>

                    {/* cert-manager */}
                    <div>
                      <p className="text-sm font-medium text-text-muted mb-2">
                        cert-manager (Kubernetes):
                      </p>
                      <div className="bg-bg text-text-main rounded-lg p-4 font-mono text-xs overflow-x-auto">
                        <pre>
                          {`apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: sentinelgrid-ejbca
spec:
  acme:
    server: ${acmeDirectory.directory_url}
    email: admin@example.com
    privateKeySecretRef:
      name: sentinelgrid-acme-key`}
                        </pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SCEP Tab */}
      {activeTab === 'scep' && (
        <div className="space-y-6">
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-main mb-4">
              SCEP (Simple Certificate Enrollment Protocol)
            </h2>
            <p className="text-sm text-text-muted mb-6">
              SCEP is designed for network devices like routers, firewalls, and switches.
              Compatible with Cisco, Juniper, Palo Alto, and Windows devices.
            </p>

            {scepEndpoint && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">
                    SCEP Endpoint URL
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      readOnly
                      value={scepEndpoint.scep_endpoint_url}
                      className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface-hover font-mono text-sm"
                    />
                    <button
                      onClick={() => copyToClipboard(scepEndpoint.scep_endpoint_url)}
                      className="px-4 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">
                    CA Certificate URL
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      readOnly
                      value={scepEndpoint.ca_certificate_url}
                      className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface-hover font-mono text-sm"
                    />
                    <button
                      onClick={() => copyToClipboard(scepEndpoint.ca_certificate_url)}
                      className="px-4 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    <strong>Note:</strong> {scepEndpoint.instructions.description}
                  </p>
                  <p className="text-sm text-blue-700 mt-2">
                    {scepEndpoint.instructions.usage}
                  </p>
                  <p className="text-sm text-blue-700 mt-1">
                    {scepEndpoint.instructions.password}
                  </p>
                </div>

                {/* Example Configurations */}
                <div className="mt-6 border-t border-surface-card-border pt-6">
                  <h3 className="text-sm font-semibold text-text-main mb-3">
                    Example Configurations
                  </h3>

                  <div className="space-y-4">
                    {/* Cisco */}
                    <div>
                      <p className="text-sm font-medium text-text-muted mb-2">
                        Cisco Router:
                      </p>
                      <div className="bg-bg text-text-main rounded-lg p-4 font-mono text-xs overflow-x-auto">
                        <pre>
                          {`crypto pki trustpoint SentinelGrid
 enrollment url ${scepEndpoint.scep_endpoint_url}
 enrollment mode ra
 password <SCEP_PASSWORD>
 revocation-check crl`}
                        </pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* EST Tab */}
      {activeTab === 'est' && (
        <div className="space-y-6">
          <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-main mb-4">
              EST (Enrollment over Secure Transport)
            </h2>
            <p className="text-sm text-text-muted mb-6">
              EST is designed for modern network devices and IoT devices. Uses HTTPS for
              secure certificate enrollment.
            </p>

            {estEndpoints && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">
                    CA Certificates URL
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      readOnly
                      value={estEndpoints.cacerts_url}
                      className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface-hover font-mono text-sm"
                    />
                    <button
                      onClick={() => copyToClipboard(estEndpoints.cacerts_url)}
                      className="px-4 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-text-muted mb-1">
                      Simple Enroll URL
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        readOnly
                        value={estEndpoints.simpleenroll_url}
                        className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface-hover font-mono text-xs"
                      />
                      <button
                        onClick={() => copyToClipboard(estEndpoints.simpleenroll_url)}
                        className="px-3 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text-muted mb-1">
                      Simple Re-enroll URL
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        readOnly
                        value={estEndpoints.simplereenroll_url}
                        className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface-hover font-mono text-xs"
                      />
                      <button
                        onClick={() => copyToClipboard(estEndpoints.simplereenroll_url)}
                        className="px-3 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    <strong>Note:</strong> {estEndpoints.instructions.description}
                  </p>
                  <p className="text-sm text-blue-700 mt-2">
                    {estEndpoints.instructions.usage}
                  </p>
                  <p className="text-sm text-blue-700 mt-1">
                    Authentication: {estEndpoints.instructions.authentication}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
