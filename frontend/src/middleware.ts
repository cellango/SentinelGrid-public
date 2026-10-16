import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware for authentication and routing
 * - Protects dashboard routes (requires authentication)
 * - Redirects authenticated users away from marketing pages
 * - Handles HTTPS redirects in development
 */
export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  const legacyRedirect = getLegacyDashboardRedirect(pathname);
  if (legacyRedirect) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = legacyRedirect;
    return NextResponse.redirect(redirectUrl, 307);
  }

  // Use the server-visible auth cookie as the route-protection source of truth.
  const token = request.cookies.get('access_token')?.value;
  const isAuthenticated = !!token;

  // Handle HTTPS redirect in development
  const host = request.headers.get('host') || '';
  const isLocalhost = host.includes('localhost') || host.includes('127.0.0.1');
  const protocol = request.headers.get('x-forwarded-proto') || 
                   (request.url.startsWith('https://') ? 'https' : 'http');
  
  // DISABLED: HTTP to HTTPS redirect for dev environment
  // Enable in production by setting NEXT_PUBLIC_FORCE_HTTPS=true
  const forceHttps = process.env.NEXT_PUBLIC_FORCE_HTTPS === 'true';
  if (forceHttps && isLocalhost && protocol === 'http' && !pathname.startsWith('/_next') && !pathname.startsWith('/api')) {
    const url = request.nextUrl.clone();
    url.protocol = 'https:';
    url.port = '3443';
    return NextResponse.redirect(url, 301);
  }
  
  if (!isAuthenticated && pathname.startsWith('/dashboard')) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = '/login';
    loginUrl.searchParams.set('next', pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isAuthenticated && (pathname === '/login' || pathname === '/signup')) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

function getLegacyDashboardRedirect(pathname: string): string | null {
  const exactRedirects: Record<string, string> = {
    '/compliance': '/dashboard/compliance',
    '/compliance/coverage': '/dashboard/compliance',
    '/compliance/ai-activity': '/dashboard/compliance/ai-activity',
    '/compliance/evidence': '/dashboard/compliance/evidence',
    '/compliance/reports': '/dashboard/compliance/reports',
    '/compliance/reports/schedule': '/dashboard/compliance/reports/schedule',
    '/dashboard/compliance/coverage': '/dashboard/compliance',
    '/iam/catalog': '/dashboard/iam/people',
    '/dashboard/iam/catalog': '/dashboard/iam/people',
    '/siem': '/dashboard/siem',
    '/siem/detection-rules': '/dashboard/siem/detection-rules',
    '/siem/detection-rules/builder': '/dashboard/siem/detection-rules/builder',
    '/siem/detection-rules/health': '/dashboard/siem/detection-rules/health',
    '/siem/detections': '/dashboard/siem/detections',
  };

  if (exactRedirects[pathname]) {
    return exactRedirects[pathname];
  }

  if (pathname.startsWith('/siem/detection-rules/')) {
    return pathname.replace('/siem/detection-rules/', '/dashboard/siem/detection-rules/');
  }

  if (pathname.startsWith('/compliance/coverage/')) {
    return '/dashboard/compliance';
  }

  if (pathname.startsWith('/dashboard/compliance/coverage/')) {
    return '/dashboard/compliance';
  }

  return null;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
