import type { NextConfig } from 'next'

const isDev = process.env.NODE_ENV === 'development'

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: isDev
          ? 'http://localhost:8000/api/:path*'
          : `${process.env.RAILWAY_API_URL}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
