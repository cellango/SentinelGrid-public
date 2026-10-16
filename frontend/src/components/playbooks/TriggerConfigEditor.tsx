/**
 * Trigger Config Editor Component
 * Edit playbook trigger conditions (wrapper component)
 */

'use client';

import { TriggerCondition } from '@/lib/api/automated-response';

interface TriggerConfigEditorProps {
  conditions: TriggerCondition;
  onChange: (conditions: TriggerCondition) => void;
}

export default function TriggerConfigEditor({
  conditions,
  onChange,
}: TriggerConfigEditorProps) {
  // This is a wrapper component that can be used for more advanced editing
  // For now, the TriggerConditionBuilder handles the editing
  return null;
}

