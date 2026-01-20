/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Production optimizations
  output: 'standalone', // Enable standalone output for optimized production builds
  
  // Image optimization
  images: {
    domains: [
      'localhost',
      // Add your production image domains here if needed
    ],
    // Allow external images if needed
    remotePatterns: [
      // Add remote image patterns here if needed
    ],
  },
  
  // Environment variables exposed to client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig
