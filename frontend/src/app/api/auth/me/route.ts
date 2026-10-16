import { NextRequest, NextResponse } from 'next/server';

const IAM_AGENT_URL =
  process.env.IAM_AGENT_URL || process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005';

export async function GET(request: NextRequest) {
  try {
    const accessToken = request.cookies.get('access_token')?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: 'Missing access token' }, { status: 401 });
    }

    const backendResponse = await fetch(`${IAM_AGENT_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      cache: 'no-store',
    });

    const data = await backendResponse.json().catch(() => ({}));

    return NextResponse.json(data, { status: backendResponse.status });
  } catch (error: any) {
    return NextResponse.json(
      { detail: error.message || 'Failed to resolve current user' },
      { status: 500 }
    );
  }
}
