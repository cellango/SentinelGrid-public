/**
 * Policy Templates Component
 * Gallery and selector for policy templates
 */

'use client';

import { useState } from 'react';
import { policyTemplates, PolicyTemplate, getTemplatesByCategory, searchTemplates } from '@/lib/policy/templates';

interface PolicyTemplatesProps {
  onSelectTemplate: (template: PolicyTemplate) => void;
  onClose: () => void;
}

const CATEGORIES: Array<{ value: PolicyTemplate['category']; label: string }> = [
  { value: 'security', label: 'Security' },
  { value: 'access', label: 'Access Control' },
  { value: 'time', label: 'Time-Based' },
  { value: 'location', label: 'Location-Based' },
  { value: 'compliance', label: 'Compliance' },
];

export function PolicyTemplates({ onSelectTemplate, onClose }: PolicyTemplatesProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<PolicyTemplate['category'] | 'all'>('all');

  const filteredTemplates =
    selectedCategory === 'all'
      ? searchQuery
        ? searchTemplates(searchQuery)
        : policyTemplates
      : getTemplatesByCategory(selectedCategory).filter((template) =>
          searchQuery
            ? searchTemplates(searchQuery).includes(template)
            : true
        );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-4xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-text-main">Policy Templates</h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-muted text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Search and Filter */}
        <div className="mb-4 space-y-3">
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedCategory('all')}
              className={`px-3 py-1 text-xs rounded-md ${
                selectedCategory === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-bg-alt text-text-muted hover:bg-surface-hover'
              }`}
            >
              All
            </button>
            {CATEGORIES.map((category) => (
              <button
                key={category.value}
                onClick={() => setSelectedCategory(category.value)}
                className={`px-3 py-1 text-xs rounded-md ${
                  selectedCategory === category.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-bg-alt text-text-muted hover:bg-surface-hover'
                }`}
              >
                {category.label}
              </button>
            ))}
          </div>
        </div>

        {/* Template Grid */}
        <div className="flex-1 overflow-y-auto">
          {filteredTemplates.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <p>No templates found matching your criteria.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredTemplates.map((template) => (
                <div
                  key={template.id}
                  className="border border-surface-card-border rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                  onClick={() => {
                    onSelectTemplate(template);
                    onClose();
                  }}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-text-main">{template.name}</h3>
                    <span
                      className={`px-2 py-0.5 text-xs rounded ${
                        template.category === 'security'
                          ? 'bg-red-100 text-red-800'
                          : template.category === 'access'
                          ? 'bg-blue-100 text-blue-800'
                          : template.category === 'time'
                          ? 'bg-orange-100 text-orange-800'
                          : template.category === 'location'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-purple-100 text-purple-800'
                      }`}
                    >
                      {CATEGORIES.find((c) => c.value === template.category)?.label || template.category}
                    </span>
                  </div>

                  <p className="text-sm text-text-muted mb-3">{template.description}</p>

                  <div className="flex items-center justify-between">
                    <div className="flex gap-1 flex-wrap">
                      {template.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 text-xs bg-bg-alt text-text-muted rounded"
                        >
                          {tag}
                        </span>
                      ))}
                      {template.tags.length > 3 && (
                        <span className="px-2 py-0.5 text-xs text-text-muted">
                          +{template.tags.length - 3}
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-text-muted">
                      {template.nodes.length} node{template.nodes.length !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

