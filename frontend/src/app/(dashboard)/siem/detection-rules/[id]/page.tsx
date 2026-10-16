import { redirect } from 'next/navigation';

export default async function DetectionRuleDetailRedirectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/dashboard/siem/detection-rules/${id}`);
}
