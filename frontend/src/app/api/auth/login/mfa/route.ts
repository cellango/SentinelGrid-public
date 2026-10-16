import { NextRequest, NextResponse } from 'next/server';

import { setAuthCookies } from '../../_sessionCookies';
import { buildCookieSessionPayload, enforceTrustedSessionOrigin } from '@/lib/auth/serverSession';

const IAM_AGENT_URL = process.env.IAM_AGENT_URL || process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005';

export async function POST(request: NextRequest) {
  const originGuard = enforceTrustedSessionOrigin(request);
  if (originGuard) {
    return originGuard;
  }

  try {
    const body = await request.json();
    const { email, password, otp, remember_me } = body;

    const backendResponse = await fetch(`${IAM_AGENT_URL}/api/v1/auth/login/mfa`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        otp,
        remember_me: remember_me || false,
      }),
    });

    const data = await backendResponse.json().catch(() => ({}));

    if (!backendResponse.ok) {
      return NextResponse.json(
        { detail: data.detail || 'MFA login failed' },
        { status: backendResponse.status }
      );
    }

    const response = NextResponse.json(buildCookieSessionPayload(data), { status: 200 });
    setAuthCookies(request, response, {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      rememberMe: !!remember_me,
    });
    return response;
  } catch (error: any) {
    console.error('MFA login API route error:', error);
    return NextResponse.json(
      { detail: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
