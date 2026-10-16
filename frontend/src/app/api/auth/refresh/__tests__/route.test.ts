/** @jest-environment node */

import { NextRequest } from 'next/server';

import { POST } from '../route';

function makeNextRequest(
  body: Record<string, unknown>,
  headers: Record<string, string> = {}
) {
  return new NextRequest('http://localhost:3000/api/auth/refresh', {
    method: 'POST',
    headers: {
      host: 'localhost:3000',
      origin: 'http://localhost:3000',
      'content-type': 'application/json',
      ...headers,
    },
    body: JSON.stringify(body),
  });
}

describe('POST /api/auth/refresh', () => {
  let fetchMock: jest.Mock;

  beforeEach(() => {
    fetchMock = jest.fn();
    global.fetch = fetchMock;
  });

  afterEach(() => {
    delete (global as typeof globalThis & { fetch?: typeof fetch }).fetch;
  });

  it('refreshes the session and updates auth cookies', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
          user: { tenant_id: 'tenant-123' },
        }),
        {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }
      )
    );

    const response = await POST(
      makeNextRequest(
        { refresh_token: 'refresh-123', remember_me: true },
        { cookie: 'refresh_token=refresh-123' }
      )
    );

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8005/api/v1/auth/refresh',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: 'refresh-123' }),
      })
    );
    expect(response.status).toBe(200);
    expect(response.cookies.get('access_token')?.value).toBe('new-access-token');
    expect(response.cookies.get('refresh_token')?.value).toBe('new-refresh-token');
    expect(response.cookies.get('auth_session_persistence')?.value).toBe('persistent');
    expect(response.headers.get('set-cookie')).toContain('HttpOnly');
    expect(response.headers.get('set-cookie')).toContain('Max-Age=604800');
    await expect(response.json()).resolves.toEqual({
      user: { tenant_id: 'tenant-123' },
      session: {
        authenticated: true,
        transport: 'cookie',
      },
    });
  });

  it('clears auth cookies when refresh fails', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Refresh failed' }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      })
    );

    const response = await POST(
      makeNextRequest({}, { cookie: 'refresh_token=refresh-123' })
    );

    expect(response.status).toBe(401);
    expect(response.cookies.get('access_token')?.value).toBe('');
    expect(response.cookies.get('refresh_token')?.value).toBe('');
    expect(response.cookies.get('auth_session_persistence')?.value).toBe('');
  });

  it('rejects cross-site refresh attempts before contacting IAM', async () => {
    const response = await POST(
      makeNextRequest(
        {},
        {
          cookie: 'refresh_token=refresh-123',
          origin: 'https://evil.example',
        }
      )
    );

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual({
      detail: 'Cross-site session mutation blocked',
    });
  });
});
