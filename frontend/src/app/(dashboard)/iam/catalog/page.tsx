import { redirect } from 'next/navigation';

export default function IAMCatalogRedirectPage() {
  redirect('/dashboard/iam/people');
}
