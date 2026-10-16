/**
 * Next.js API route for login that sets cookie server-side
 * This eliminates timing issues with client-side cookie setting
 */

import { NextRequest, NextResponse } from 'next/server';

import { setAuthCookies } from '../_sessionCookies';
import { buildCookieSessionPayload, enforceTrustedSessionOrigin } from '@/lib/auth/serverSession';

// Use localhost for development (frontend runs on host, not in Docker)
// Per ports.md: IAM Agent external port is 8005
const IAM_AGENT_URL = process.env.IAM_AGENT_URL || process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005';

export async function POST(request: NextRequest) {
  const originGuard = enforceTrustedSessionOrigin(request);
  if (originGuard) {
    return originGuard;
  }

  try {
    const body = await request.json();
    const { email, password, remember_me } = body;

    // Call backend login API
    const backendResponse = await fetch(`${IAM_AGENT_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        remember_me: remember_me || false,
      }),
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      // Return error response with same status code and headers
      const errorHeaders: Record<string, string> = {};
      backendResponse.headers.forEach((value, key) => {
        errorHeaders[key] = value;
      });
      
      return NextResponse.json(
        { detail: data.detail || 'Login failed' },
        { status: backendResponse.status, headers: errorHeaders }
      );
    }

    // Create response with login data
    const response = NextResponse.json(buildCookieSessionPayload(data), { status: 200 });

    setAuthCookies(request, response, {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      rememberMe: !!remember_me,
    });

    return response;
  } catch (error: any) {
    console.error('Login API route error:', error);
    return NextResponse.json(
      { detail: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
