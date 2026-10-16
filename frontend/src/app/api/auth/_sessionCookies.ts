import { NextRequest, NextResponse } from 'next/server';

const PERSISTENT_SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60;
const SESSION_PERSISTENCE_COOKIE = 'auth_session_persistence';

function shouldUseSecureCookie(request: NextRequest): boolean {
  const forwardedProto = request.headers.get('x-forwarded-proto');
  const protocol = forwardedProto || request.nextUrl.protocol.replace(':', '');
  const host = request.headers.get('host') || request.nextUrl.host;
  const isLocalhost = host.includes('localhost') || host.includes('127.0.0.1');

  return protocol === 'https' && !isLocalhost;
}

function buildCookieOptions(request: NextRequest, rememberMe: boolean) {
  const options: {
    path: string;
    httpOnly: boolean;
    secure: boolean;
    sameSite: 'lax';
    maxAge?: number;
  } = {
    path: '/',
    httpOnly: true,
    secure: shouldUseSecureCookie(request),
    sameSite: 'lax',
  };

  if (rememberMe) {
    options.maxAge = PERSISTENT_SESSION_MAX_AGE_SECONDS;
  }

  return options;
}

export function setAuthCookies(
  request: NextRequest,
  response: NextResponse,
  {
    accessToken,
    refreshToken,
    rememberMe = false,
  }: {
  accessToken: string;
  refreshToken?: string | null;
  rememberMe?: boolean;
  }
) {
  const cookieOptions = buildCookieOptions(request, rememberMe);
  const persistenceCookieOptions = {
    path: '/',
    httpOnly: false,
    secure: cookieOptions.secure,
    sameSite: 'lax' as const,
    ...(rememberMe ? { maxAge: PERSISTENT_SESSION_MAX_AGE_SECONDS } : {}),
  };

  response.cookies.set('access_token', accessToken, cookieOptions);
  if (refreshToken) {
    response.cookies.set('refresh_token', refreshToken, cookieOptions);
  }
  response.cookies.set(
    SESSION_PERSISTENCE_COOKIE,
    rememberMe ? 'persistent' : 'session',
    persistenceCookieOptions
  );
}

export function clearAuthCookies(request: NextRequest, response: NextResponse) {
  const cookieOptions = buildCookieOptions(request, false);
  const clearOptions = {
    ...cookieOptions,
    expires: new Date(0),
    maxAge: 0,
  };

  response.cookies.set('access_token', '', clearOptions);
  response.cookies.set('refresh_token', '', clearOptions);
  response.cookies.set(SESSION_PERSISTENCE_COOKIE, '', clearOptions);
}
