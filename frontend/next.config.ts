import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // !! WARN !!
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors.
    // !! WARN !!
    ignoreBuildErrors: true,
  },
  
  // Essential for Docker deployment
  output: 'standalone',

  async redirects() {
    return [
      {
        source: '/register',
        destination: '/sign-up',
        permanent: true,
      },
    ];
  },
  
  // Proxy API requests to the backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_BACKEND_BASE_URL}/api/:path*`,
      },
      {
        source: '/docs',
        destination: `${process.env.NEXT_PUBLIC_BACKEND_BASE_URL}/docs`,
      },
      {
        source: '/openapi.json',
        destination: `${process.env.NEXT_PUBLIC_BACKEND_BASE_URL}/openapi.json`,
      },
      {
        source: '/health',
        destination: `${process.env.NEXT_PUBLIC_BACKEND_BASE_URL}/health`,
      },
    ];
  },
  
  // Image configuration for Docker
  images: {
    // If you're using external images, add domains here
    // domains: ['example.com', 'cdn.example.com'],
    
    // Alternative: use remotePatterns for more control
    // remotePatterns: [
    //   {
    //     protocol: 'https',
    //     hostname: 'example.com',
    //   },
    // ],
  },
  
  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ];
  },
  
  // Optional: Ensure trailing slashes are handled consistently
  trailingSlash: false,
  
  // Optional: Configure asset prefix if needed
  // assetPrefix: process.env.ASSET_PREFIX || '',
  
  // Performance optimizations
  reactStrictMode: true,
  
  // Compression
  compress: true,
};

export default nextConfig;
