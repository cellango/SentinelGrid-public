import { NextRequest, NextResponse } from 'next/server';
import { resolveSessionAuthorization } from '@/lib/auth/serverSession';

const IAM_AGENT_URL =
  process.env.IAM_AGENT_URL || process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005';

export async function GET(request: NextRequest) {
  const authHeader = resolveSessionAuthorization(request);
  if (!authHeader) {
    return NextResponse.json({ detail: 'Missing authorization header' }, { status: 401 });
  }

  const search = request.nextUrl.search || '';
  const targetUrl = `${IAM_AGENT_URL}/api/v1/devices${search}`;

  try {
    const response = await fetch(targetUrl, {
      headers: { Authorization: authHeader },
      cache: 'no-store',
    });

    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('❌ Devices proxy error:', error);
    return NextResponse.json({ detail: 'Failed to fetch devices' }, { status: 500 });
  }
}
