/** @jest-environment node */

import { NextRequest } from 'next/server';

import { POST } from '../route';

function makeNextRequest(body: Record<string, unknown>, headers: Record<string, string> = {}) {
  return new NextRequest('http://localhost:3000/api/auth/login', {
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

describe('POST /api/auth/login', () => {
  let fetchMock: jest.Mock;
  let logSpy: jest.SpyInstance;
  let errorSpy: jest.SpyInstance;

  beforeEach(() => {
    fetchMock = jest.fn();
    global.fetch = fetchMock;
    logSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    logSpy.mockRestore();
    errorSpy.mockRestore();
    delete (global as typeof globalThis & { fetch?: typeof fetch }).fetch;
  });

  it('forwards credentials to the IAM login endpoint', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: 'token-123',
          refresh_token: 'refresh-123',
          user: { tenant_id: 'tenant-123' },
        }),
        {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }
      )
    );

    await POST(
      makeNextRequest({
        email: 'analyst@example.com',
        password: 'DemoPassword123!',
        remember_me: false,
      })
    );

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8005/api/v1/auth/login',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'analyst@example.com',
          password: 'DemoPassword123!',
          remember_me: false,
        }),
      })
    );
  });

  it('sets a session cookie without max-age when remember_me is false', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: 'token-123',
          refresh_token: 'refresh-123',
          user: { tenant_id: 'tenant-123' },
        }),
        {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }
      )
    );

    const response = await POST(
      makeNextRequest({
        email: 'analyst@example.com',
        password: 'DemoPassword123!',
        remember_me: false,
      })
    );

    const accessCookie = response.cookies.get('access_token');
    const refreshCookie = response.cookies.get('refresh_token');
    const persistenceCookie = response.cookies.get('auth_session_persistence');
    const payload = await response.json();

    expect(accessCookie?.value).toBe('token-123');
    expect(refreshCookie?.value).toBe('refresh-123');
    expect(persistenceCookie?.value).toBe('session');
    expect(response.headers.get('set-cookie')).not.toContain('Max-Age=');
    expect(response.headers.get('set-cookie')).toContain('HttpOnly');
    expect(payload).toEqual({
      user: { tenant_id: 'tenant-123' },
      session: {
        authenticated: true,
        transport: 'cookie',
      },
    });
    expect(payload).not.toHaveProperty('access_token');
    expect(payload).not.toHaveProperty('refresh_token');
  });

  it('sets a persistent cookie with max-age when remember_me is true', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: 'token-123',
          refresh_token: 'refresh-123',
          user: { tenant_id: 'tenant-123' },
        }),
        {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }
      )
    );

    const response = await POST(
      makeNextRequest({
        email: 'analyst@example.com',
        password: 'DemoPassword123!',
        remember_me: true,
      })
    );

    const cookie = response.cookies.get('access_token');
    const persistenceCookie = response.cookies.get('auth_session_persistence');

    expect(cookie?.value).toBe('token-123');
    expect(persistenceCookie?.value).toBe('persistent');
    expect(response.headers.get('set-cookie')).toContain('Max-Age=604800');
  });

  it('returns the upstream error status and detail when backend login fails', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Invalid credentials' }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      })
    );

    const response = await POST(
      makeNextRequest({
        email: 'analyst@example.com',
        password: 'wrong-password',
      })
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: 'Invalid credentials' });
  });

  it('rejects cross-site login attempts that try to mutate the cookie-backed session', async () => {
    const response = await POST(
      makeNextRequest(
        {
          email: 'analyst@example.com',
          password: 'DemoPassword123!',
        },
        { origin: 'https://evil.example' }
      )
    );

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual({
      detail: 'Cross-site session mutation blocked',
    });
  });
});
