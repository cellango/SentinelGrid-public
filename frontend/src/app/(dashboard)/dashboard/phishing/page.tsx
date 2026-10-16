'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPhishingReports, PhishingReport, PhishingFilters } from '@/lib/api/phishing';
import PhishingReportCard from '@/components/phishing/PhishingReportCard';
import PhishingFiltersComponent from '@/components/phishing/PhishingFilters';
import { toast } from 'react-hot-toast';
import { useRouter } from 'next/navigation';

export default function PhishingQueuePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<PhishingFilters>({
    limit: 50,
    offset: 0,
  });
  const [searchQuery, setSearchQuery] = useState('');

  // Get tenant ID from context or localStorage (you may need to adjust this)
  const tenantId = typeof window !== 'undefined' 
    ? localStorage.getItem('tenant_id') || ''
    : '';

  const { data: reports, isLoading, error } = useQuery<PhishingReport[], Error>({
    queryKey: ['phishingReports', tenantId, filters],
    queryFn: () => getPhishingReports(tenantId, filters),
    enabled: !!tenantId,
  });

  useEffect(() => {
    if (error) {
      toast.error(`Failed to load phishing reports: ${error.message}`);
    }
  }, [error]);

  const handleFilterChange = (newFilters: Partial<PhishingFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters, offset: 0 }));
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // TODO: Implement search functionality (may need backend support)
  };

  const filteredReports = reports?.filter((report) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      report.subject?.toLowerCase().includes(query) ||
      report.from_address.toLowerCase().includes(query) ||
      report.reported_by?.toLowerCase().includes(query)
    );
  }) || [];

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-bg-alt rounded w-1/4"></div>
          <div className="h-10 bg-bg-alt rounded"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-24 bg-bg-alt rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-text-main">Phishing Reports</h1>
        <div className="text-sm text-text-muted">
          {filteredReports.length} {filteredReports.length === 1 ? 'report' : 'reports'}
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search by subject, sender, or reporter..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full px-4 py-2 bg-surface-dark border border-surface-card-border rounded-lg text-text-main placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <PhishingFiltersComponent filters={filters} onFilterChange={handleFilterChange} />
        </div>

        {/* Reports List */}
        <div className="lg:col-span-3">
          {filteredReports.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <p className="text-lg mb-2">No phishing reports found</p>
              <p className="text-sm">
                {searchQuery || Object.keys(filters).length > 2
                  ? 'Try adjusting your filters or search query'
                  : 'Reports will appear here when emails are ingested'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredReports.map((report) => (
                <PhishingReportCard
                  key={report.id}
                  report={report}
                  onClick={() => router.push(`/dashboard/phishing/${report.id}`)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

