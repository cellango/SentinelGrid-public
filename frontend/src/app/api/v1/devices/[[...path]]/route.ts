'use server';

import { NextRequest, NextResponse } from 'next/server';
import { resolveSessionAuthorization } from '@/lib/auth/serverSession';

const IAM_AGENT_URL =
  process.env.IAM_AGENT_URL || process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005';

/**
 * Catch-all proxy for device APIs so `/api/v1/devices` (and subpaths) work in Next.
 */
async function proxy(req: NextRequest, extraPath: string[]) {
  const authHeader = resolveSessionAuthorization(req);
  if (!authHeader) {
    return NextResponse.json({ detail: 'Missing authorization header' }, { status: 401 });
  }

  const search = req.nextUrl.search || '';
  const pathSuffix = extraPath.length ? `/${extraPath.join('/')}` : '';
  const targetUrl = `${IAM_AGENT_URL}/api/v1/devices${pathSuffix}${search}`;

  try {
    const init: RequestInit = {
      method: req.method,
      headers: {
        Authorization: authHeader,
        'Content-Type': req.headers.get('content-type') || 'application/json',
      },
      cache: 'no-store',
    };

    if (req.method !== 'GET' && req.method !== 'HEAD') {
      init.body = await req.arrayBuffer();
    }

    const response = await fetch(targetUrl, init);
    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch (err) {
    console.error('❌ Devices proxy error:', err);
    return NextResponse.json({ detail: 'Failed to proxy devices request' }, { status: 500 });
  }
}

type DevicesRouteContext = {
  params: Promise<{ path?: string[] }>;
};

export async function GET(req: NextRequest, { params }: DevicesRouteContext) {
  const { path = [] } = await params;
  return proxy(req, path);
}

export async function POST(req: NextRequest, { params }: DevicesRouteContext) {
  const { path = [] } = await params;
  return proxy(req, path);
}

export async function PATCH(req: NextRequest, { params }: DevicesRouteContext) {
  const { path = [] } = await params;
  return proxy(req, path);
}

export async function DELETE(req: NextRequest, { params }: DevicesRouteContext) {
  const { path = [] } = await params;
  return proxy(req, path);
}
