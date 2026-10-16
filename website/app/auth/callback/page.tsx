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

    // Exchange code for token
    const exchangeCodeForToken = async () => {
      try {
        const keycloakUrl = process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'http://localhost:8081';
        const realm = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'sentinelgrid';
        const clientId = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'sentinelgrid-frontend';
        const redirectUri = window.location.origin + '/auth/callback';

        const response = await fetch(
          `${keycloakUrl}/realms/${realm}/protocol/openid-connect/token`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
              grant_type: 'authorization_code',
              code: code,
              client_id: clientId,
              redirect_uri: redirectUri,
            }),
          }
        );

        if (!response.ok) {
          throw new Error('Token exchange failed');
        }

        const data = await response.json();
        
        // Store tokens
        localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token);
        }

        // Decode token to get user info (simple base64 decode)
        try {
          const payload = JSON.parse(atob(data.access_token.split('.')[1]));
          const user = {
            id: payload.sub,
            email: payload.email || payload.preferred_username || 'unknown',
            roles: payload.realm_access?.roles || [],
          };
          localStorage.setItem('user', JSON.stringify(user));
          
          // Get tenant_id from token or fetch from API
          // For now, we'll use a default or fetch from API
          const tenantId = payload.tenant_id || payload['tenant-id'] || null;
          if (tenantId) {
            localStorage.setItem('tenant_id', tenantId);
          } else {
            // Fetch tenant_id from API using the token
            try {
              const apiBase = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';
              const tenantResponse = await fetch(`${apiBase}/api/v1/iam/users/me`, {
                headers: {
                  'Authorization': `Bearer ${data.access_token}`,
                },
              });
              if (tenantResponse.ok) {
                const tenantData = await tenantResponse.json();
                if (tenantData.tenant_id) {
                  localStorage.setItem('tenant_id', tenantData.tenant_id);
                }
              }
            } catch (e) {
              console.error('Failed to fetch tenant_id', e);
            }
          }
        } catch (e) {
          console.error('Failed to decode token', e);
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
    <main className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
        <p className="text-slate-300">Completing sign in...</p>
      </div>
    </main>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-300">Loading...</p>
        </div>
      </main>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}

