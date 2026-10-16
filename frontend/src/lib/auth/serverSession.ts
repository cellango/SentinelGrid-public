import { NextRequest, NextResponse } from 'next/server';

import { isSessionAuthorizationHeader } from './sessionContract';

type AuthUser = {
  id: string;
  email: string;
  tenant_id: string;
  roles: string[];
  plan_tier?: string;
};

type BrowserSessionPayload = {
  user: AuthUser;
  expires_in?: number;
  token_type?: string;
  signup_completed?: boolean;
  password_reset_required?: boolean;
  realm?: string;
  session: {
    authenticated: true;
    transport: 'cookie';
  };
};

function normalizeOrigin(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function getAllowedOrigins(request: NextRequest): Set<string> {
  const origins = new Set<string>();
  const requestOrigin = normalizeOrigin(request.nextUrl.origin);

  if (requestOrigin) {
    origins.add(requestOrigin);
  }

  [
    process.env.NEXT_PUBLIC_APP_URL,
    process.env.NEXT_PUBLIC_SITE_URL,
    process.env.PUBLIC_APP_BASE_URL,
  ]
    .map((candidate) => normalizeOrigin(candidate))
    .filter((candidate): candidate is string => Boolean(candidate))
    .forEach((candidate) => origins.add(candidate));

  return origins;
}

export function enforceTrustedSessionOrigin(request: NextRequest): NextResponse | null {
  const origin = normalizeOrigin(request.headers.get('origin'));
  if (!origin) {
    return null;
  }

  if (getAllowedOrigins(request).has(origin)) {
    return null;
  }

  return NextResponse.json({ detail: 'Cross-site session mutation blocked' }, { status: 403 });
}

export function resolveSessionAuthorization(request: NextRequest): string | null {
  const authorization = request.headers.get('authorization');
  if (authorization && !isSessionAuthorizationHeader(authorization)) {
    return authorization;
  }

  const accessToken = request.cookies.get('access_token')?.value;
  if (!accessToken) {
    return null;
  }

  return `Bearer ${accessToken}`;
}

export function buildCookieSessionPayload(data: Record<string, any>): BrowserSessionPayload {
  const payload: BrowserSessionPayload = {
    user: data.user,
    session: {
      authenticated: true,
      transport: 'cookie',
    },
  };

  if (typeof data.expires_in === 'number') {
    payload.expires_in = data.expires_in;
  }
  if (typeof data.token_type === 'string') {
    payload.token_type = data.token_type;
  }
  if (typeof data.signup_completed === 'boolean') {
    payload.signup_completed = data.signup_completed;
  }
  if (typeof data.password_reset_required === 'boolean') {
    payload.password_reset_required = data.password_reset_required;
  }
  if (typeof data.realm === 'string') {
    payload.realm = data.realm;
  }

  return payload;
}
