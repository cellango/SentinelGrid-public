/**
 * App Catalog Page
 * Browse and connect prebuilt applications for SSO
 */

'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import { MagnifyingGlassIcon, Squares2X2Icon, CheckCircleIcon } from '@heroicons/react/24/outline';
import AppConnectorWizard from '@/components/iam/AppConnectorWizard';

// Use relative URLs to leverage Next.js rewrites
const API_BASE = '';

interface AppCatalogItem {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  app_type: string;
  protocol: string;
  icon_url?: string;
  category?: string;
  required_fields: string[];
  optional_fields: string[];
}

async function getAppCatalog(category?: string, search?: string): Promise<{ items: AppCatalogItem[]; total: number }> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (search) params.append('search', search);

  const response = await fetch(`/api/iam-portal/catalog/apps?${params.toString()}`, {
    credentials: 'include',
  });
  return response.json();
}

async function connectApp(appId: string, config: Record<string, any>): Promise<{ success: boolean; app_id: string; client_id: string; message: string }> {
  const response = await fetch(`/api/iam-portal/catalog/apps/${appId}/connect`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ catalog_app_id: appId, config }),
  });
  return response.json();
}

export default function AppCatalogPage() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedApp, setSelectedApp] = useState<AppCatalogItem | null>(null);
  const [showWizard, setShowWizard] = useState(false);

  const { data: catalog, isLoading } = useQuery({
    queryKey: ['app-catalog', selectedCategory, searchQuery],
    queryFn: () => getAppCatalog(selectedCategory, searchQuery),
    enabled: isAuthenticated,
  });

  const connectMutation = useMutation({
    mutationFn: ({ appId, config }: { appId: string; config: Record<string, any> }) =>
      connectApp(appId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['app-catalog'] });
      queryClient.invalidateQueries({ queryKey: ['iam-apps'] });
      setShowWizard(false);
      setSelectedApp(null);
    },
  });

  const categories = [
    'All',
    'Productivity',
    'Communication',
    'Development',
    'CRM',
    'Finance',
    'Storage',
  ];

  const handleConnect = (app: AppCatalogItem) => {
    setSelectedApp(app);
    setShowWizard(true);
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-text-muted">Loading app catalog...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-main">App Catalog</h1>
        <p className="text-sm text-text-muted mt-1">
          Connect prebuilt applications for single sign-on (SSO)
        </p>
      </div>

      {/* Search and Filters */}
      <div className="mb-6 space-y-4">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-muted" />
            <input
              type="text"
              placeholder="Search apps..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Category Filters */}
        <div className="flex gap-2 flex-wrap">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category === 'All' ? '' : category)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                (category === 'All' && !selectedCategory) || selectedCategory === category
                  ? 'bg-blue-600 text-white'
                  : 'bg-bg-alt text-text-muted hover:bg-surface-hover'
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* App Grid */}
      {catalog && catalog.items.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {catalog.items.map((app) => (
            <div
              key={app.id}
              className="bg-surface-card border border-surface-card-border rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  {app.icon_url ? (
                    <img src={app.icon_url} alt={app.display_name} className="w-12 h-12 rounded-lg" />
                  ) : (
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Squares2X2Icon className="w-6 h-6 text-blue-600" />
                    </div>
                  )}
                  <div>
                    <h3 className="font-semibold text-text-main">{app.display_name}</h3>
                    {app.category && (
                      <span className="text-xs text-text-muted">{app.category}</span>
                    )}
                  </div>
                </div>
              </div>

              {app.description && (
                <p className="text-sm text-text-muted mb-4 line-clamp-2">{app.description}</p>
              )}

              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs px-2 py-1 bg-bg-alt text-text-muted rounded">
                  {app.protocol}
                </span>
                <span className="text-xs px-2 py-1 bg-bg-alt text-text-muted rounded">
                  {app.app_type}
                </span>
              </div>

              <button
                onClick={() => handleConnect(app)}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                Connect
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-surface-card border border-surface-card-border rounded-lg">
          <Squares2X2Icon className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">No apps found</p>
          {searchQuery && (
            <p className="text-sm text-text-muted mt-2">
              Try adjusting your search or filters
            </p>
          )}
        </div>
      )}

      {/* App Connector Wizard */}
      {showWizard && selectedApp && (
        <AppConnectorWizard
          app={selectedApp}
          onClose={() => {
            setShowWizard(false);
            setSelectedApp(null);
          }}
          onConnect={(config) => {
            connectMutation.mutate({ appId: selectedApp.id, config });
          }}
          isLoading={connectMutation.isPending}
        />
      )}
    </div>
  );
}
