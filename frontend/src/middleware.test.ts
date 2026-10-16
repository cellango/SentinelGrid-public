/** @jest-environment node */

import { NextRequest } from 'next/server';

import { middleware } from './middleware';

function makeRequest(path: string, headers: Record<string, string> = {}) {
  return new NextRequest(`http://localhost:3000${path}`, {
    headers,
  });
}

describe('frontend middleware auth routing', () => {
  it('redirects unauthenticated dashboard requests to login', () => {
    const response = middleware(makeRequest('/dashboard/incidents'));

    expect(response?.status).toBe(307);
    expect(response?.headers.get('location')).toBe(
      'http://localhost:3000/login?next=%2Fdashboard%2Fincidents'
    );
  });

  it('redirects authenticated login requests back to dashboard', () => {
    const response = middleware(
      makeRequest('/login', { cookie: 'access_token=token-123' })
    );

    expect(response?.status).toBe(307);
    expect(response?.headers.get('location')).toBe('http://localhost:3000/dashboard');
  });

  it('allows public routes without auth', () => {
    const response = middleware(makeRequest('/pricing'));

    expect(response?.headers.get('x-middleware-next')).toBe('1');
  });
});
