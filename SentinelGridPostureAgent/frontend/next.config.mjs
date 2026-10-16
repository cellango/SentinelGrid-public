/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8100',
    NEXT_PUBLIC_MCP_URL: process.env.NEXT_PUBLIC_MCP_URL || 'http://localhost:8102',
  },
};

export default nextConfig;

