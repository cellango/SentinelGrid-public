import { NextRequest, NextResponse } from 'next/server';

import { clearAuthCookies } from '../_sessionCookies';
import { enforceTrustedSessionOrigin } from '@/lib/auth/serverSession';

const IAM_AGENT_URL = process.env.IAM_AGENT_URL || process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005';

export async function POST(request: NextRequest) {
  let detail = 'Logged out';
  const originGuard = enforceTrustedSessionOrigin(request);
  if (originGuard) {
    return originGuard;
  }

  try {
    const body = await request.json().catch(() => ({}));
    const refreshToken = body.refresh_token || request.cookies.get('refresh_token')?.value;

    if (refreshToken) {
      const backendResponse = await fetch(`${IAM_AGENT_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      const data = await backendResponse.json().catch(() => ({}));
      if (backendResponse.ok && data.detail) {
        detail = data.detail;
      }
    }
  } catch (error) {
    console.error('Logout API route error:', error);
  }

  const response = NextResponse.json({ success: true, detail }, { status: 200 });
  clearAuthCookies(request, response);
  return response;
}
