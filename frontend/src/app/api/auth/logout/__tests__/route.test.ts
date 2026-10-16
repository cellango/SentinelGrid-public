/** @jest-environment node */

import { NextRequest } from 'next/server';

import { POST } from '../route';

function makeNextRequest(
  body: Record<string, unknown> = {},
  headers: Record<string, string> = {}
) {
  return new NextRequest('http://localhost:3000/api/auth/logout', {
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

describe('POST /api/auth/logout', () => {
  let fetchMock: jest.Mock;
  let errorSpy: jest.SpyInstance;

  beforeEach(() => {
    fetchMock = jest.fn();
    global.fetch = fetchMock;
    errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    errorSpy.mockRestore();
    delete (global as typeof globalThis & { fetch?: typeof fetch }).fetch;
  });

  it('forwards logout to IAM and clears auth cookies', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Backend logout complete' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    );

    const response = await POST(
      makeNextRequest({}, { cookie: 'refresh_token=refresh-123' })
    );

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8005/api/v1/auth/logout',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: 'refresh-123' }),
      })
    );
    expect(response.status).toBe(200);
    expect(response.cookies.get('access_token')?.value).toBe('');
    expect(response.cookies.get('refresh_token')?.value).toBe('');
    expect(response.cookies.get('auth_session_persistence')?.value).toBe('');
    await expect(response.json()).resolves.toEqual({
      success: true,
      detail: 'Backend logout complete',
    });
  });

  it('still clears cookies when backend logout errors', async () => {
    fetchMock.mockRejectedValue(new Error('IAM unavailable'));

    const response = await POST(
      makeNextRequest({}, { cookie: 'refresh_token=refresh-123' })
    );

    expect(response.status).toBe(200);
    expect(response.cookies.get('access_token')?.value).toBe('');
    expect(response.cookies.get('refresh_token')?.value).toBe('');
    expect(response.cookies.get('auth_session_persistence')?.value).toBe('');
    await expect(response.json()).resolves.toEqual({
      success: true,
      detail: 'Logged out',
    });
  });

  it('rejects cross-site logout attempts before contacting IAM', async () => {
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
