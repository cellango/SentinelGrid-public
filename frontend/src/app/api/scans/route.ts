import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  // Proxy to backend /scans endpoint. Assumes gateway enforces auth/tenant scoping.
  const base = process.env.NEXT_PUBLIC_API_BASE || '';
  const res = await fetch(`${base}/scans`, {
    headers: {
      cookie: req.headers.get('cookie') || '',
      'x-tenant-id': req.headers.get('x-tenant-id') || '',
    },
    cache: 'no-store',
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    return NextResponse.json(body || { error: 'Failed to fetch scans' }, { status: res.status });
  }
  const data = await res.json();
  return NextResponse.json(data);
}
