/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
  async redirects() {
    return [
      { source: '/dashboard/alerts', destination: '/alerts', permanent: false },
      { source: '/dashboard/logs', destination: '/logs', permanent: false },
      { source: '/dashboard/threats', destination: '/threats', permanent: false },
      { source: '/dashboard/vulnerabilities', destination: '/vulnerabilities', permanent: false },
      { source: '/dashboard/assets', destination: '/assets', permanent: false },
      { source: '/dashboard/ai-analyst', destination: '/ai-analyst', permanent: false },
      { source: '/dashboard/reports', destination: '/reports', permanent: false },
      { source: '/dashboard/settings', destination: '/settings', permanent: false },
    ];
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
