'use client';

import { SESSION_AUTHORIZATION_HEADER, SESSION_AUTH_MARKER } from './sessionContract';

type AuthUser = {
  id: string;
  email: string;
  tenant_id: string;
  roles: string[];
  plan_tier?: string;
};

type AuthMetadata = {
  user: AuthUser;
  realm?: string;
};

let hasInMemorySession = false;

export function setInMemoryAccessToken(token: string | null) {
  hasInMemorySession = !!token;
}

export function getInMemoryAccessToken(): string | null {
  return hasInMemorySession ? SESSION_AUTH_MARKER : null;
}

export function withSessionAuthorization(headers: Record<string, string> = {}) {
  const accessToken = getInMemoryAccessToken();
  if (!accessToken) {
    return headers;
  }

  return {
    ...headers,
    Authorization: SESSION_AUTHORIZATION_HEADER,
  };
}

export function persistAuthMetadata({ user, realm }: AuthMetadata) {
  if (typeof window === 'undefined') return;

  localStorage.setItem('tenant_id', user.tenant_id);
  localStorage.setItem('user', JSON.stringify(user));
  localStorage.setItem('user_email', user.email);

  if (user.plan_tier) {
    localStorage.setItem('plan_tier', user.plan_tier);
  } else {
    localStorage.removeItem('plan_tier');
  }

  if (realm) {
    localStorage.setItem('realm', realm);
  } else {
    localStorage.removeItem('realm');
  }
}

export function clearAuthMetadata() {
  if (typeof window === 'undefined') return;

  setInMemoryAccessToken(null);
  localStorage.removeItem('tenant_id');
  localStorage.removeItem('user');
  localStorage.removeItem('user_email');
  localStorage.removeItem('realm');
  localStorage.removeItem('plan_tier');
  localStorage.removeItem('login_response');
}
