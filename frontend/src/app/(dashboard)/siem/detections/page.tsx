import { redirect } from 'next/navigation';

export default function DetectionsRedirectPage() {
  redirect('/dashboard/siem/detections');
}
