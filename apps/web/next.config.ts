import type { NextConfig } from 'next'

const isDev = process.env.NODE_ENV === 'development'
const RAILWAY_API_URL = process.env.RAILWAY_API_URL

if (!isDev && !RAILWAY_API_URL) {
  throw new Error(
    'RAILWAY_API_URL is not set. Add it to Vercel environment variables before deploying.'
  )
}

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: isDev
          ? 'http://localhost:8000/api/:path*'
          : `${RAILWAY_API_URL}/api/:path*`,
      },
    ]
  },

  allowedDevOrigins: ['localhost:3000', '127.0.0.1:3000'],
}

export default nextConfig
