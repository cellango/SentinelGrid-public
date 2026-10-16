'use client';

import React, { useState, useEffect } from 'react';
import { HardenedImage, getRecommendedImages } from '@/lib/api/hardened-images';

interface ImageSelectionProps {
  cloudProvider: string;
  region?: string;
  selectedImageId?: string;
  onImageSelect: (image: HardenedImage) => void;
  onSkip?: () => void;
}

export default function ImageSelection({
  cloudProvider,
  region,
  selectedImageId,
  onImageSelect,
  onSkip,
}: ImageSelectionProps) {
  const [images, setImages] = useState<HardenedImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<HardenedImage | null>(null);

  useEffect(() => {
    async function fetchImages() {
      try {
        setLoading(true);
        setError(null);
        const recommendedImages = await getRecommendedImages(cloudProvider, region);
        setImages(recommendedImages);
        
        // Pre-select if image ID provided
        if (selectedImageId) {
          const preSelected = recommendedImages.find(img => img.id === selectedImageId || img.image_id === selectedImageId);
          if (preSelected) {
            setSelectedImage(preSelected);
            onImageSelect(preSelected);
          }
        }
      } catch (err: any) {
        console.error('Error fetching images:', err);
        setError(err.message || 'Failed to load hardened images');
      } finally {
        setLoading(false);
      }
    }

    if (cloudProvider) {
      fetchImages();
    }
  }, [cloudProvider, region, selectedImageId, onImageSelect]);

  const handleImageSelect = (image: HardenedImage) => {
    setSelectedImage(image);
    onImageSelect(image);
  };

  const getCloudProviderName = (provider: string) => {
    const names: Record<string, string> = {
      aws: 'AWS',
      azure: 'Azure',
      gcp: 'Google Cloud',
    };
    return names[provider] || provider.toUpperCase();
  };

  const getOSIcon = (osName: string) => {
    if (osName.toLowerCase().includes('ubuntu')) return '🐧';
    if (osName.toLowerCase().includes('amazon')) return '📦';
    if (osName.toLowerCase().includes('rhel') || osName.toLowerCase().includes('red hat')) return '🔴';
    if (osName.toLowerCase().includes('debian')) return '🔵';
    if (osName.toLowerCase().includes('windows')) return '🪟';
    return '💻';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading hardened images...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Select a Hardened OS Image
        </h3>
        <p className="text-sm text-gray-600">
          Choose a pre-hardened OS image with SentinelGrid Endpoint Protection Agent pre-installed.
          These images are built with CIS Level 1 hardening and ready to use.
        </p>
      </div>

      {images.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">
            No hardened images available for {getCloudProviderName(cloudProvider)}.
            You can skip this step and install the agent manually later.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {images.map((image) => (
            <div
              key={image.id}
              onClick={() => handleImageSelect(image)}
              className={`
                border-2 rounded-lg p-4 cursor-pointer transition-all
                ${
                  selectedImage?.id === image.id
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }
              `}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">{getOSIcon(image.os_name)}</span>
                    <div>
                      <h4 className="font-semibold text-gray-900">
                        {image.os_name} {image.os_version}
                      </h4>
                      <p className="text-xs text-gray-500">
                        {image.hardening_level}
                      </p>
                    </div>
                  </div>
                  
                  <div className="space-y-1 text-sm text-gray-600">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Cloud:</span>
                      <span>{getCloudProviderName(image.cloud_provider)}</span>
                    </div>
                    {image.region && (
                      <div className="flex items-center gap-2">
                        <span className="font-medium">Region:</span>
                        <span>{image.region}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Agent:</span>
                      <span className="flex items-center gap-1">
                        {image.agent_installed ? (
                          <>
                            <span className="text-green-600">✓</span>
                            <span>v{image.agent_version}</span>
                          </>
                        ) : (
                          <span className="text-gray-400">Not installed</span>
                        )}
                      </span>
                    </div>
                    {image.cis_benchmark_version && (
                      <div className="flex items-center gap-2">
                        <span className="font-medium">CIS:</span>
                        <span>v{image.cis_benchmark_version}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Built:</span>
                      <span>{new Date(image.build_date).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                
                {selectedImage?.id === image.id && (
                  <div className="ml-2">
                    <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between pt-4 border-t">
        <button
          onClick={onSkip}
          className="text-sm text-gray-600 hover:text-gray-800 underline"
        >
          Skip for now
        </button>
        
        <div className="text-xs text-gray-500">
          {selectedImage
            ? `Selected: ${selectedImage.os_name} ${selectedImage.os_version}`
            : 'Select an image to continue'}
        </div>
      </div>
    </div>
  );
}

