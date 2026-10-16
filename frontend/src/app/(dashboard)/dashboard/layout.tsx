'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { getOnboardingStatus } from '@/lib/api/onboarding';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [loading, setLoading] = useState(true);

  // Check onboarding status and handle redirects
  useEffect(() => {
    const checkOnboarding = async () => {
      if (typeof window === 'undefined') {
        setLoading(false);
        return;
      }

      // Only check onboarding for exact /dashboard or /dashboard/welcome paths.
      // Skip all sub-routes (IAM, SIEM, etc.) to avoid interfering with navigation.
      if (pathname !== '/dashboard' && pathname !== '/dashboard/welcome') {
        setLoading(false);
        return;
      }

      console.log(`📍 Dashboard sublayout checking onboarding for path: ${pathname}`);

      // Check onboarding status
      try {
        const status = await getOnboardingStatus();

        // If onboarding complete and user is on welcome, send them to dashboard once.
        if (status.onboarding_completed && pathname === '/dashboard/welcome') {
          console.log('✅ Onboarding complete, redirecting from welcome to dashboard');
          router.replace('/dashboard');
          return;
        }

        // If onboarding is NOT complete:
        // - Let /dashboard/welcome stay (config flow)
        // - Allow /dashboard to remain (no redirect loop), but higher-level UI should show a banner.
        console.log(`ℹ️ Onboarding status: ${status.onboarding_completed ? 'complete' : 'incomplete'}; staying on ${pathname}`);
      } catch (error) {
        console.error('Error checking onboarding status:', error);
        // Do not redirect on error; avoid bounce loops.
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(checkOnboarding, 100);
    return () => clearTimeout(timer);
  }, [router, pathname]);

  // Show loading while checking onboarding status
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

  // Just pass through children - parent layout handles navigation
  return <>{children}</>;
}
