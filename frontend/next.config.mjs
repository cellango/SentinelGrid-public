import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  outputFileTracingRoot: __dirname,
  poweredByHeader: false,
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080',
  },
  webpack: (config) => {
    config.resolve.alias['@'] = path.resolve(__dirname, 'src');
    return config;
  },
  // Rewrite API calls to backend services
  // Order matters: more specific routes should come first
  async rewrites() {
    return [
      // Certificate Service API routes (must come before general API Gateway route)
      {
        source: '/api/v1/:path(certificates|ca|enrollment|bootstrap-tokens)/:rest*',
        // Inside the Docker network the cert_service listens on 8000 (8015 is host-mapped only)
        destination: `${process.env.CERT_SERVICE_URL || 'http://cert_service:8000'}/api/v1/:path/:rest*`,
      },
      // IAM Agent API routes (includes self-service + user onboarding)
      {
        source: '/api/v1/:path(auth|payment|agents|hardened-images|git-providers|git-scanning|leads|secrets|api-keys|self|users|devices)/:rest*',
        destination: `${process.env.IAM_AGENT_URL || 'http://iam_agent:8000'}/api/v1/:path/:rest*`,
      },
      // Access requests → IAM Agent
      {
        source: '/api/v1/access-requests/:rest*',
        destination: `${process.env.IAM_AGENT_URL || 'http://iam_agent:8000'}/api/v1/access-requests/:rest*`,
      },
      {
        source: '/api/iam-portal/:path*',
        destination: `${process.env.IAM_AGENT_URL || 'http://iam_agent:8000'}/api/iam-portal/:path*`,
      },
      {
        source: '/api/iam-policies/:path*',
        destination: `${process.env.IAM_AGENT_URL || 'http://iam_agent:8000'}/api/iam-policies/:path*`,
      },
      // API Gateway routes (all other /api calls - must be last)
      {
        source: '/api/:path*',
        destination: `${process.env.API_GATEWAY_URL || 'http://api_gateway:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
