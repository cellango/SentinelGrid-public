import { NextRequest, NextResponse } from 'next/server';
import { resolveSessionAuthorization } from '@/lib/auth/serverSession';

/**
 * Server-side proxy to Reporting via API Gateway to avoid browser mixed-content/redirects.
 * Forwards Authorization, X-Tenant-ID, X-Realm headers.
 */
export async function GET(req: NextRequest) {
  const auth = resolveSessionAuthorization(req);
  const tenantId = req.headers.get('x-tenant-id');
  const realm = req.headers.get('x-realm');
  const qs = req.nextUrl.searchParams.toString();
  const target = `http://api_gateway:8000/api/v1/reports/${qs ? `?${qs}` : ''}`;

  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (auth) headers['Authorization'] = auth;
  if (tenantId) headers['X-Tenant-ID'] = tenantId;
  if (realm) headers['X-Realm'] = realm;

  const resp = await fetch(target, {
    method: 'GET',
    headers,
    redirect: 'follow',
  });

  const body = await resp.text();
  return new NextResponse(body, {
    status: resp.status,
    headers: { 'content-type': resp.headers.get('content-type') || 'application/json' },
  });
}
