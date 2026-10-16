/**
 * Hardened Image Selector
 * Modern UI for browsing and selecting hardened OS images
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getRecommendedImages, listHardenedImages, type HardenedImage } from '@/lib/api/hardened-images';
import Link from 'next/link';

interface HardenedImageSelectorProps {
  tenantId: string;
  cloudProvider?: string;
  region?: string;
}

export default function HardenedImageSelector({ tenantId, cloudProvider = 'aws', region }: HardenedImageSelectorProps) {
  const [selectedProvider, setSelectedProvider] = useState(cloudProvider);
  const [selectedRegion, setSelectedRegion] = useState(region);
  const [selectedImage, setSelectedImage] = useState<HardenedImage | null>(null);

  const { data: images = [], isLoading } = useQuery({
    queryKey: ['hardened-images', selectedProvider, selectedRegion],
    queryFn: () => getRecommendedImages(selectedProvider, selectedRegion),
    enabled: !!selectedProvider,
  });
  const imagesArray = Array.isArray(images) ? images : [];

  const getOSIcon = (osName: string) => {
    const lower = osName.toLowerCase();
    if (lower.includes('ubuntu')) return '🐧';
    if (lower.includes('amazon') || lower.includes('amzn')) return '📦';
    if (lower.includes('rhel') || lower.includes('red hat')) return '🔴';
    if (lower.includes('debian')) return '🔵';
    if (lower.includes('windows')) return '🪟';
    return '💻';
  };

  const getProviderName = (provider: string) => {
    const names: Record<string, string> = {
      aws: 'AWS',
      azure: 'Azure',
      gcp: 'Google Cloud',
    };
    return names[provider] || provider.toUpperCase();
  };

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-semibold text-text-main mb-1">Hardened Images</h3>
          <p className="text-sm text-text-muted">
            Pre-hardened OS images with SentinelGrid agent pre-installed
          </p>
        </div>
        <Link
          href="/dashboard/endpoint-protection#images"
          className="px-4 py-2 bg-primary/20 text-primary rounded-xl hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/30"
        >
          View All
        </Link>
      </div>

      {/* Provider Filter */}
      <div className="flex gap-2 mb-4">
        {['aws', 'azure', 'gcp'].map((provider) => (
          <button
            key={provider}
            onClick={() => {
              setSelectedProvider(provider);
              setSelectedImage(null);
            }}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              selectedProvider === provider
                ? 'bg-primary/20 text-primary border border-primary/30'
                : 'bg-[rgba(15,23,42,0.9)] text-text-muted border border-primary/10 hover:border-primary/20'
            }`}
          >
            {getProviderName(provider)}
          </button>
        ))}
      </div>

      {/* Images Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
        </div>
      ) : imagesArray.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-4">📦</div>
          <p className="text-text-muted mb-2">No hardened images available</p>
          <p className="text-sm text-text-muted">Check back later or install the agent manually</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {imagesArray.slice(0, 4).map((image) => (
            <ImageCard
              key={image.id}
              image={image}
              isSelected={selectedImage?.id === image.id}
              onSelect={() => setSelectedImage(image)}
              getOSIcon={getOSIcon}
              getProviderName={getProviderName}
            />
          ))}
        </div>
      )}

      {/* Selected Image Actions */}
      {selectedImage && (
        <div className="mt-4 p-4 bg-primary/10 border border-primary/20 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text-main mb-1">
                Selected: {selectedImage.os_name} {selectedImage.os_version}
              </p>
              <p className="text-xs text-text-muted">
                {getProviderName(selectedImage.cloud_provider)} • {selectedImage.region || 'All regions'}
              </p>
            </div>
            <div className="flex gap-2">
              {selectedImage.download_url && (
                <a
                  href={selectedImage.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/30"
                >
                  Download
                </a>
              )}
              <button className="px-3 py-1.5 bg-gradient-to-r from-primary to-secondary text-slate-950 rounded-lg hover:brightness-110 transition-all text-sm font-medium">
                Launch Instance
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ImageCard({
  image,
  isSelected,
  onSelect,
  getOSIcon,
  getProviderName,
}: {
  image: HardenedImage;
  isSelected: boolean;
  onSelect: () => void;
  getOSIcon: (os: string) => string;
  getProviderName: (provider: string) => string;
}) {
  return (
    <div
      onClick={onSelect}
      className={`border-2 rounded-xl p-4 cursor-pointer transition-all hover:scale-[1.02] ${
        isSelected
          ? 'border-primary bg-primary/10 shadow-lg shadow-primary/20'
          : 'border-primary/20 bg-[rgba(15,23,42,0.9)] hover:border-primary/40'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="text-3xl">{getOSIcon(image.os_name)}</div>
          <div>
            <h4 className="font-semibold text-text-main">
              {image.os_name} {image.os_version}
            </h4>
            <p className="text-xs text-text-muted">{image.hardening_level}</p>
          </div>
        </div>
        {isSelected && (
          <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
            <svg className="w-4 h-4 text-slate-950" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
      </div>

      <div className="space-y-1.5 text-xs text-text-muted">
        <div className="flex items-center justify-between">
          <span>Cloud:</span>
          <span className="text-text-main">{getProviderName(image.cloud_provider)}</span>
        </div>
        {image.region && (
          <div className="flex items-center justify-between">
            <span>Region:</span>
            <span className="text-text-main">{image.region}</span>
          </div>
        )}
        <div className="flex items-center justify-between">
          <span>Agent:</span>
          <span className="text-text-main">
            {image.agent_installed ? `v${image.agent_version} ✓` : 'Not installed'}
          </span>
        </div>
        {image.cis_benchmark_version && (
          <div className="flex items-center justify-between">
            <span>CIS:</span>
            <span className="text-text-main">v{image.cis_benchmark_version}</span>
          </div>
        )}
      </div>
    </div>
  );
}
