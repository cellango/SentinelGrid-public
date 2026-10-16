import React, { useState } from 'react';
import { PhishingReport } from '@/lib/api/phishing';
import clsx from 'clsx';

interface ActionButtonsProps {
  report: PhishingReport;
  onClassify: () => void;
  onUpdate: (updates: { classification?: string; status?: string; severity?: string }) => void;
  isClassifying: boolean;
  onRunContainment?: () => void;
  isRunningContainment?: boolean;
}

interface ActionButtonsProps {
  report: PhishingReport;
  onClassify: () => void;
  onUpdate: (updates: { classification?: string; status?: string; severity?: string }) => void;
  isClassifying: boolean;
}

const ActionButtons: React.FC<ActionButtonsProps> = ({
  report,
  onClassify,
  onUpdate,
  isClassifying,
  onRunContainment,
  isRunningContainment = false,
}) => {
  const [showConfirm, setShowConfirm] = useState<string | null>(null);

  const handleMarkAsPhishing = () => {
    onUpdate({
      classification: 'phishing',
      status: 'confirmed_phishing',
    });
    setShowConfirm(null);
  };

  const handleMarkAsBenign = () => {
    onUpdate({
      classification: 'benign',
      status: 'confirmed_benign',
    });
    setShowConfirm(null);
  };

  return (
    <div className="flex flex-wrap gap-2">
      {!report.classification && (
        <button
          onClick={onClassify}
          disabled={isClassifying}
          className={clsx(
            'px-4 py-2 rounded-lg font-medium transition-colors',
            isClassifying
              ? 'bg-border text-text-muted cursor-not-allowed'
              : 'bg-primary text-white hover:bg-primary-dark'
          )}
        >
          {isClassifying ? 'Classifying...' : 'Classify Email'}
        </button>
      )}

      {showConfirm !== 'phishing' && showConfirm !== 'benign' && (
        <>
          <button
            onClick={() => setShowConfirm('phishing')}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Mark as Phishing
          </button>
          <button
            onClick={() => setShowConfirm('benign')}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Mark as Benign
          </button>
        </>
      )}

      {showConfirm === 'phishing' && (
        <div className="flex gap-2">
          <button
            onClick={handleMarkAsPhishing}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Confirm Phishing
          </button>
          <button
            onClick={() => setShowConfirm(null)}
            className="px-4 py-2 bg-border text-white rounded-lg hover:bg-surface-hover transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {showConfirm === 'benign' && (
        <div className="flex gap-2">
          <button
            onClick={handleMarkAsBenign}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Confirm Benign
          </button>
          <button
            onClick={() => setShowConfirm(null)}
            className="px-4 py-2 bg-border text-white rounded-lg hover:bg-surface-hover transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Run Containment Playbook */}
      {report.classification === 'phishing' && onRunContainment && (
        <button
          onClick={onRunContainment}
          disabled={isRunningContainment}
          className={clsx(
            'px-4 py-2 rounded-lg font-medium transition-colors',
            isRunningContainment
              ? 'bg-border text-text-muted cursor-not-allowed'
              : 'bg-orange-600 text-white hover:bg-orange-700'
          )}
        >
          {isRunningContainment ? 'Running Containment...' : 'Run Containment Playbook'}
        </button>
      )}
    </div>
  );
};

export default ActionButtons;

