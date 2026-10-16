import { NextRequest, NextResponse } from 'next/server';

import { setAuthCookies } from '../_sessionCookies';
import { buildCookieSessionPayload, enforceTrustedSessionOrigin } from '@/lib/auth/serverSession';

const KEYCLOAK_URL =
  process.env.KEYCLOAK_URL || process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'http://localhost:8081';
const KEYCLOAK_REALM =
  process.env.KEYCLOAK_REALM || process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'sentinelgrid';
const KEYCLOAK_CLIENT_ID =
  process.env.KEYCLOAK_CLIENT_ID || process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'sentinelgrid-frontend';

function decodeJwtPayload(token: string): Record<string, any> {
  const [, payload = ''] = token.split('.');
  return JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
}

export async function POST(request: NextRequest) {
  const originGuard = enforceTrustedSessionOrigin(request);
  if (originGuard) {
    return originGuard;
  }

  try {
    const body = await request.json().catch(() => ({}));
    const code = typeof body.code === 'string' ? body.code : '';
    const redirectUri =
      typeof body.redirect_uri === 'string'
        ? body.redirect_uri
        : `${request.nextUrl.origin}/auth/callback`;

    if (!code) {
      return NextResponse.json({ detail: 'Missing authorization code' }, { status: 400 });
    }

    const tokenResponse = await fetch(
      `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'authorization_code',
          code,
          client_id: KEYCLOAK_CLIENT_ID,
          redirect_uri: redirectUri,
        }),
      }
    );

    const tokenData = await tokenResponse.json().catch(() => ({}));

    if (!tokenResponse.ok) {
      return NextResponse.json(
        { detail: tokenData.error_description || tokenData.error || 'Token exchange failed' },
        { status: tokenResponse.status }
      );
    }

    const payload = decodeJwtPayload(tokenData.access_token);
    const user = {
      id: payload.sub,
      email: payload.email || payload.preferred_username || 'unknown',
      tenant_id: payload.tenant_id || payload['tenant-id'] || '',
      roles: payload.realm_access?.roles || [],
      plan_tier: payload.plan_tier,
    };
    const realm =
      typeof payload.iss === 'string' && payload.iss.includes('/realms/')
        ? payload.iss.split('/realms/').pop()
        : KEYCLOAK_REALM;

    const response = NextResponse.json(
      buildCookieSessionPayload({
        user,
        realm,
      }),
      { status: 200 }
    );

    setAuthCookies(request, response, {
      accessToken: tokenData.access_token,
      refreshToken: tokenData.refresh_token,
      rememberMe: false,
    });

    return response;
  } catch (error: any) {
    return NextResponse.json(
      { detail: error.message || 'Failed to exchange authorization code' },
      { status: 500 }
    );
  }
}
