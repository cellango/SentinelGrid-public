/**
 * Reports Management Page
 * List, generate, and manage reports
 */

'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listTemplates, generateReport, listReports, deleteReport, ReportTemplate, Report } from '@/lib/api/reports';
import Link from 'next/link';
import { toast } from 'react-hot-toast';

export default function ReportsPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [format, setFormat] = useState<'pdf' | 'csv'>('pdf');

  const queryClient = useQueryClient();

  // Fetch templates
  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['report-templates'],
    queryFn: () => listTemplates(),
  });

  // Fetch reports
  const { data: reports, isLoading: reportsLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: () => listReports({ limit: 50 }),
  });

  // Generate report mutation
  const generateMutation = useMutation({
    mutationFn: generateReport,
    onSuccess: () => {
      toast.success('Report generation started. Check back in a moment.');
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to generate report');
    },
  });

  // Delete report mutation
  const deleteMutation = useMutation({
    mutationFn: deleteReport,
    onSuccess: () => {
      toast.success('Report deleted');
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete report');
    },
  });

  const handleGenerate = () => {
    if (!selectedTemplate) {
      toast.error('Please select a template');
      return;
    }

    generateMutation.mutate({
      template_id: selectedTemplate,
      format,
      date_range: dateRange.start && dateRange.end ? dateRange : undefined,
    });
  };

  const handleDelete = (reportId: string) => {
    if (confirm('Are you sure you want to delete this report?')) {
      deleteMutation.mutate(reportId);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-500';
      case 'generating':
        return 'text-blue-500';
      case 'failed':
        return 'text-red-500';
      default:
        return 'text-yellow-500';
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-main mb-2">Reports</h1>
        <p className="text-text-muted">Generate and manage security reports</p>
      </div>

      {/* Generate Report Section */}
      <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6 mb-8">
        <h2 className="text-xl font-semibold text-text-main mb-4">Generate New Report</h2>

        <div className="space-y-4">
          {/* Template Selection */}
          <div>
            <label className="block text-sm font-medium text-text-main mb-2">
              Report Template
            </label>
            {templatesLoading ? (
              <p className="text-text-muted">Loading templates...</p>
            ) : (
              <select
                value={selectedTemplate || ''}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full rounded-md bg-bg-alt border-border text-text-main shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2"
              >
                <option value="">Select a template...</option>
                {templates?.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name} ({template.type})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-text-main mb-2">Format</label>
            <div className="flex gap-4">
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  value="pdf"
                  checked={format === 'pdf'}
                  onChange={(e) => setFormat(e.target.value as 'pdf')}
                  className="form-radio text-primary focus:ring-primary"
                />
                <span className="ml-2 text-text-main">PDF</span>
              </label>
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  value="csv"
                  checked={format === 'csv'}
                  onChange={(e) => setFormat(e.target.value as 'csv')}
                  className="form-radio text-primary focus:ring-primary"
                />
                <span className="ml-2 text-text-main">CSV</span>
              </label>
            </div>
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-main mb-2">Start Date</label>
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="w-full rounded-md bg-bg-alt border-border text-text-main shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-main mb-2">End Date</label>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="w-full rounded-md bg-bg-alt border-border text-text-main shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2"
              />
            </div>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={!selectedTemplate || generateMutation.isPending}
            className="px-6 py-2 bg-primary text-bg font-semibold rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {generateMutation.isPending ? 'Generating...' : 'Generate Report'}
          </button>
        </div>
      </div>

      {/* Reports List */}
      <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
        <h2 className="text-xl font-semibold text-text-main mb-4">Generated Reports</h2>

        {reportsLoading ? (
          <p className="text-text-muted">Loading reports...</p>
        ) : reports && reports.length > 0 ? (
          <div className="space-y-3">
            {reports.map((report) => (
              <div
                key={report.id}
                className="flex items-center justify-between p-4 rounded-lg border border-[rgba(15,23,42,0.9)] hover:border-primary/30 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-medium text-text-main">{report.name}</span>
                    <span className={`text-sm font-semibold ${getStatusColor(report.status)}`}>
                      {report.status}
                    </span>
                    <span className="text-xs text-text-muted">{report.format.toUpperCase()}</span>
                  </div>
                  {report.generated_at && (
                    <p className="text-sm text-text-muted">
                      Generated: {new Date(report.generated_at).toLocaleString()}
                    </p>
                  )}
                  {report.error_message && (
                    <p className="text-sm text-red-400 mt-1">{report.error_message}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {report.status === 'completed' && report.download_url && (
                    <a
                      href={report.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 bg-primary text-bg font-semibold rounded-lg hover:bg-primary/90 transition-colors text-sm"
                    >
                      Download report
                    </a>
                  )}
                  <button
                    onClick={() => handleDelete(report.id)}
                    className="px-4 py-2 bg-red-500/20 text-red-500 font-semibold rounded-lg hover:bg-red-500/30 transition-colors text-sm"
                  >
                    Remove report
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-text-muted">No reports generated yet.</p>
        )}
      </div>
    </div>
  );
}
