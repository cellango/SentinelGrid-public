import { redirect } from 'next/navigation';

export default function DetectionRuleHealthRedirectPage() {
  redirect('/dashboard/siem/detection-rules/health');
}
