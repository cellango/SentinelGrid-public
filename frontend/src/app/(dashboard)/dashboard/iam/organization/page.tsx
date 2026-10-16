/**
 * Organization Profile Page
 * Manage organization settings, branding, and configuration
 */

'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import { getOrganization, updateOrganization, uploadLogo, type Organization, type OrganizationUpdate } from '@/lib/api/iam-organization';
import { BuildingOfficeIcon, PhotoIcon } from '@heroicons/react/24/outline';

export default function OrganizationPage() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [logoFile, setLogoFile] = useState<File | null>(null);

  const { data: organization, isLoading } = useQuery({
    queryKey: ['organization'],
    queryFn: () => getOrganization(),
    enabled: isAuthenticated,
  });

  const updateMutation = useMutation({
    mutationFn: (data: OrganizationUpdate) => updateOrganization(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
    },
  });

  const logoMutation = useMutation({
    mutationFn: (file: File) => uploadLogo(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
      setLogoFile(null);
    },
  });

  const [formData, setFormData] = useState<OrganizationUpdate>({
    name: '',
    display_name: '',
    primary_domain: '',
    domains: [],
    timezone: '',
    language: '',
    contact_email: '',
  });

  // Initialize form when organization loads
  useState(() => {
    if (organization) {
      setFormData({
        name: organization.name || '',
        display_name: organization.display_name || '',
        primary_domain: organization.primary_domain || '',
        domains: organization.domains || [],
        timezone: organization.timezone || '',
        language: organization.language || '',
        contact_email: organization.contact_email || '',
      });
    }
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  const handleLogoUpload = () => {
    if (logoFile) {
      logoMutation.mutate(logoFile);
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-text-muted">Loading organization settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-main">Organization</h1>
        <p className="text-sm text-text-muted mt-1">Manage your organization profile and settings</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-main mb-4 flex items-center gap-2">
            <BuildingOfficeIcon className="w-5 h-5" />
            Basic Information
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Organization Name *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Acme Corporation"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Display Name
              </label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Acme Corp"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Primary Domain
              </label>
              <input
                type="text"
                value={formData.primary_domain}
                onChange={(e) => setFormData({ ...formData, primary_domain: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="acme.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Contact Email
              </label>
              <input
                type="email"
                value={formData.contact_email}
                onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="admin@acme.com"
              />
              <p className="text-xs text-text-muted mt-1">
                Email for security notifications and breach communications
              </p>
            </div>
          </div>
        </div>

        {/* Logo */}
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-main mb-4 flex items-center gap-2">
            <PhotoIcon className="w-5 h-5" />
            Logo
          </h2>

          <div className="space-y-4">
            {organization?.logo_url && (
              <div className="flex items-center gap-4">
                <img
                  src={organization.logo_url}
                  alt="Organization logo"
                  className="w-24 h-24 object-contain border border-surface-card-border rounded-lg"
                />
                <div>
                  <p className="text-sm text-text-muted">Current logo</p>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Upload Logo
              </label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/svg+xml"
                onChange={(e) => setLogoFile(e.target.files?.[0] || null)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-text-muted mt-1">
                PNG, JPG, or SVG. Max 2MB.
              </p>
            </div>

            {logoFile && (
              <button
                type="button"
                onClick={handleLogoUpload}
                disabled={logoMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {logoMutation.isPending ? 'Uploading...' : 'Upload Logo'}
              </button>
            )}
          </div>
        </div>

        {/* Regional Settings */}
        <div className="bg-surface-card border border-surface-card-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-main mb-4">Regional Settings</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Timezone
              </label>
              <select
                value={formData.timezone}
                onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
              <label className="block text-sm font-medium text-text-muted mb-1">
                Language
              </label>
              <select
                value={formData.language}
                onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select language...</option>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
}
