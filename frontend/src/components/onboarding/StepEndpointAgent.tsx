'use client';

import React, { useState, useEffect } from 'react';
import ImageSelection from './ImageSelection';
import { HardenedImage } from '@/lib/api/hardened-images';
import { recheckHealth } from '@/lib/api/onboarding';

interface StepEndpointAgentProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export default function StepEndpointAgent({
  onNext,
  onBack,
  onSkip,
}: StepEndpointAgentProps) {
  const [selectedImage, setSelectedImage] = useState<HardenedImage | null>(null);
  const [cloudProvider, setCloudProvider] = useState<string>('aws');
  const [region, setRegion] = useState<string>('us-east-1');
  const [healthOk, setHealthOk] = useState(false);
  const [healthDetails, setHealthDetails] = useState<any>(null);
  const [lastTest, setLastTest] = useState<string | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get cloud provider from previous step or localStorage
  useEffect(() => {
    // TODO: Get from onboarding state or API
    const savedCloud = localStorage.getItem('onboarding_cloud_provider');
    if (savedCloud) {
      setCloudProvider(savedCloud);
    }
  }, []);

  const handleImageSelect = (image: HardenedImage) => {
    setSelectedImage(image);
    // Store selection
    localStorage.setItem('onboarding_selected_image', JSON.stringify(image));
  };

  const handleContinue = async () => {
    try {
      setHealthLoading(true);
      setError(null);
      const now = new Date().toLocaleString();
      const res = await recheckHealth('endpoint');
      const health = res?.health || null;
      const isHealthy = (health?.status || '').toLowerCase() === 'healthy';

      setHealthDetails(health);
      setHealthOk(isHealthy);
      setLastTest(now);

      if (isHealthy) {
        onNext();
        return;
      }

      setError(
        health?.message ||
          'Endpoint coverage is not registered yet. Deploy the agent and re-run validation, or skip this step and return later.'
      );
    } catch (err: any) {
      setHealthOk(false);
      setHealthDetails(null);
      setError(err.message || 'Failed to validate endpoint coverage');
    } finally {
      setHealthLoading(false);
    }
  };

  const handleRecheck = async () => {
    try {
      setHealthLoading(true);
      setError(null);
      const res = await recheckHealth('endpoint');
      setHealthDetails(res?.health || null);
      setHealthOk((res?.health?.status || '').toLowerCase() === 'healthy');
      setLastTest(new Date().toLocaleString());
    } catch (err: any) {
      setError(err.message || 'Failed to recheck endpoint health');
      setHealthOk(false);
    } finally {
      setHealthLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Deploy Endpoint Protection</h2>
        <p className="text-slate-300">
          Choose a pre-hardened OS image with SentinelGrid Endpoint Protection Agent pre-installed,
          or install the agent manually on your existing infrastructure.
        </p>
      </div>

      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-300">
          💡 <strong>Recommended:</strong> Use a hardened image for the easiest setup. These images
          include CIS Level 1 hardening and the SentinelGrid agent pre-installed.
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
          {error}
        </div>
      )}
      {healthOk && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-sm text-green-300 flex items-center justify-between">
          <span>Endpoint agent validated {lastTest ? `(${lastTest})` : ''}.</span>
          <span className="text-xs bg-green-600/20 px-2 py-1 rounded-full border border-green-500/40">Healthy</span>
        </div>
      )}
      {healthDetails && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3 text-xs text-slate-200">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-slate-200">Health details</div>
            <button
              type="button"
              onClick={handleRecheck}
              disabled={healthLoading}
              className="text-cyan-300 hover:text-cyan-200 text-xs"
            >
              {healthLoading ? 'Checking...' : 'Re-run health'}
            </button>
          </div>
          <div className="text-slate-300">{healthDetails.message || 'Validation performed'}</div>
        </div>
      )}

      {/* Image Selection */}
      {cloudProvider && (
        <ImageSelection
          cloudProvider={cloudProvider}
          region={region}
          selectedImageId={selectedImage?.id}
          onImageSelect={handleImageSelect}
          onSkip={onSkip}
        />
      )}

      {/* Manual Installation Option */}
      <div className="border-t border-slate-700 pt-6">
        <h3 className="text-lg font-semibold mb-2">Or Install Manually</h3>
        <p className="text-sm text-slate-400 mb-4">
          Install the SentinelGrid agent on your existing servers.
        </p>
        <button
          type="button"
          onClick={() => {
            // TODO: Show installation instructions
            window.open('https://docs.sentinelgrid.ai/agents/installation', '_blank');
          }}
          className="text-sm text-cyan-400 hover:text-cyan-300 underline"
        >
          View Installation Instructions →
        </button>
      </div>

      <div className="flex justify-between pt-4">
        <button
          type="button"
          onClick={onBack}
          className="text-sm text-slate-300 hover:text-slate-100"
        >
          ← Back
        </button>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onSkip}
            className="text-sm text-slate-300 hover:text-slate-100"
          >
            Skip
          </button>
          <button
            type="button"
            onClick={handleContinue}
            disabled={healthLoading}
            className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {healthLoading ? 'Validating...' : 'Validate endpoint coverage'}
          </button>
        </div>
      </div>
    </div>
  );
}
