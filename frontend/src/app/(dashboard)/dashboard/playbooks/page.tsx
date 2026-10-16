/**
 * Playbooks Page (Next.js page entry)
 * Renders the shared PlaybooksView component
 */

import { PlaybooksView } from './PlaybooksView';
import { PlanGate } from '@/components/PlanGate';

export default function PlaybooksPage() {
  return (
    <PlanGate
      requiredTier="protect_defend"
      title="Unlock automation playbooks"
      description="Playbook authoring, approval, and automation triggers are part of the Protect + Defend plan."
    >
      <PlaybooksView />
    </PlanGate>
  );
}
