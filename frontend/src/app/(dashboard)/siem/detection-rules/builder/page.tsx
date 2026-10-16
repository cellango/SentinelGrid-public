import { redirect } from 'next/navigation';

export default function DetectionRuleBuilderRedirectPage() {
  redirect('/dashboard/siem/detection-rules/builder');
}
