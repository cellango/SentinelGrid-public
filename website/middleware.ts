import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware to redirect HTTP to HTTPS
 * Only applies when FORCE_HTTPS environment variable is set
 */
export function middleware(request: NextRequest) {
  // Only redirect if explicitly enabled via environment variable
  const forceHttps = process.env.NEXT_PUBLIC_FORCE_HTTPS === 'true';
  const httpsPort = process.env.NEXT_PUBLIC_HTTPS_PORT || '3444';
  
  if (!forceHttps) {
    return NextResponse.next();
  }
  
  // Check if request is HTTP (not HTTPS)
  const host = request.headers.get('host') || '';
  const isLocalhost = host.includes('localhost') || host.includes('127.0.0.1');
  const protocol = request.headers.get('x-forwarded-proto') || 
                   (request.url.startsWith('https://') ? 'https' : 'http');
  
  // Redirect HTTP to HTTPS when forced
  // Keep traffic on the configured HTTPS port to avoid bouncing to legacy containers
  if (isLocalhost && protocol === 'http' && !request.nextUrl.pathname.startsWith('/_next')) {
    const url = request.nextUrl.clone();
    url.protocol = 'https:';
    if (!url.port || url.port === '80' || url.port === '3000') {
      url.port = httpsPort;
    }
    return NextResponse.redirect(url, 301);
  }
  
  return NextResponse.next();
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
