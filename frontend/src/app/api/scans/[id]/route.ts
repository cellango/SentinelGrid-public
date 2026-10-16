import { NextRequest, NextResponse } from 'next/server';

type ScanRouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_req: NextRequest, { params }: ScanRouteContext) {
  const { id } = await params;
  const base = process.env.NEXT_PUBLIC_API_BASE || '';
  const res = await fetch(`${base}/scans/${id}`, {
    headers: {
      // Pass through cookie and tenant headers if present in the request context (not available in route handler here).
    },
    cache: 'no-store',
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    return NextResponse.json(body || { error: 'Failed to fetch scan' }, { status: res.status });
  }
  const data = await res.json();
  return NextResponse.json(data);
}
