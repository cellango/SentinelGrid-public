'use client';

/**
 * OAuth Callback Handler
 * Handles the redirect from Keycloak after authentication
 */

import { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

// Force dynamic rendering
export const dynamic = 'force-dynamic';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    const error = searchParams.get('error');

    if (error) {
      console.error('OAuth error:', error);
      router.push('/login?error=' + encodeURIComponent(error));
      return;
    }

    if (!code) {
      console.error('No authorization code received');
      router.push('/login?error=no_code');
      return;
    }

    const exchangeCodeForToken = async () => {
      try {
        const redirectUri = window.location.origin + '/auth/callback';
        const response = await fetch('/api/auth/exchange-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            code,
            redirect_uri: redirectUri,
          }),
        });

        if (!response.ok) {
          throw new Error('Token exchange failed');
        }

        // Redirect to dashboard
        router.push('/dashboard');
      } catch (error) {
        console.error('Authentication error:', error);
        router.push('/login?error=auth_failed');
      }
    };

    exchangeCodeForToken();
  }, [router, searchParams]);

  return (
    <main className="min-h-screen bg-bg text-text-main flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
        <p className="text-text-muted">Completing sign in...</p>
      </div>
    </main>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-bg text-text-main flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-text-muted">Loading...</p>
        </div>
      </main>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}
