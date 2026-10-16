import { NextRequest, NextResponse } from 'next/server';

import { clearAuthCookies, setAuthCookies } from '../_sessionCookies';
import { buildCookieSessionPayload, enforceTrustedSessionOrigin } from '@/lib/auth/serverSession';

const IAM_AGENT_URL = process.env.IAM_AGENT_URL || process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005';

export async function POST(request: NextRequest) {
  const originGuard = enforceTrustedSessionOrigin(request);
  if (originGuard) {
    return originGuard;
  }

  try {
    const body = await request.json().catch(() => ({}));
    const refreshToken = body.refresh_token || request.cookies.get('refresh_token')?.value;
    const persistenceCookie = request.cookies.get('auth_session_persistence')?.value;
    const rememberMe =
      body.remember_me === true ||
      body.rememberMe === true ||
      persistenceCookie === 'persistent';

    if (!refreshToken) {
      const response = NextResponse.json({ detail: 'Missing refresh_token' }, { status: 400 });
      clearAuthCookies(request, response);
      return response;
    }

    const backendResponse = await fetch(`${IAM_AGENT_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const data = await backendResponse.json().catch(() => ({}));

    if (!backendResponse.ok) {
      const response = NextResponse.json(
        { detail: data.detail || 'Token refresh failed' },
        { status: backendResponse.status }
      );
      clearAuthCookies(request, response);
      return response;
    }

    const response = NextResponse.json(buildCookieSessionPayload(data), { status: 200 });
    setAuthCookies(request, response, {
      accessToken: data.access_token,
      refreshToken: data.refresh_token || refreshToken,
      rememberMe,
    });
    return response;
  } catch (error: any) {
    const response = NextResponse.json(
      { detail: error.message || 'Internal server error' },
      { status: 500 }
    );
    clearAuthCookies(request, response);
    return response;
  }
}
