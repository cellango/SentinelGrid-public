/** @jest-environment node */

import { NextRequest } from 'next/server';

import { GET } from '../route';

function makeNextRequest(headers: Record<string, string> = {}) {
  return new NextRequest('http://localhost:3000/api/auth/me', {
    method: 'GET',
    headers: {
      host: 'localhost:3000',
      origin: 'http://localhost:3000',
      ...headers,
    },
  });
}

describe('GET /api/auth/me', () => {
  let fetchMock: jest.Mock;

  beforeEach(() => {
    fetchMock = jest.fn();
    global.fetch = fetchMock;
  });

  afterEach(() => {
    delete (global as typeof globalThis & { fetch?: typeof fetch }).fetch;
  });

  it('returns 401 when the access cookie is missing', async () => {
    const response = await GET(makeNextRequest());

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: 'Missing access token' });
  });

  it('forwards the cookie-backed token to the IAM auth me endpoint', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'user-1',
          email: 'analyst@example.com',
          tenant_id: 'tenant-123',
          roles: ['SOC_ANALYST'],
          realm: 'sentinelgrid',
          plan_tier: 'protect',
        }),
        {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }
      )
    );

    const response = await GET(
      makeNextRequest({ cookie: 'access_token=token-123' })
    );

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8005/api/v1/auth/me',
      expect.objectContaining({
        method: 'GET',
        headers: {
          Authorization: 'Bearer token-123',
        },
        cache: 'no-store',
      })
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      id: 'user-1',
      email: 'analyst@example.com',
      tenant_id: 'tenant-123',
      roles: ['SOC_ANALYST'],
      realm: 'sentinelgrid',
      plan_tier: 'protect',
    });
  });
});
