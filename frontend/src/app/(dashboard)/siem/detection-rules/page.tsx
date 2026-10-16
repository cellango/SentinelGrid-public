import { redirect } from 'next/navigation';

export default function DetectionRulesRedirectPage() {
  redirect('/dashboard/siem/detection-rules');
}
