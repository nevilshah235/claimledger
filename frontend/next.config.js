/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config, { isServer, webpack }) => {
    // Handle Circle SDK and its Node.js dependencies
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
        stream: false,
        url: false,
        zlib: false,
        http: false,
        https: false,
        assert: false,
        os: false,
        path: false,
      };
      
      // Mark Circle SDK and its problematic dependencies as externals
      // This prevents Next.js from trying to bundle them
      config.externals = config.externals || [];
      config.externals.push({
        '@circle-fin/w3s-pw-web-sdk': 'commonjs @circle-fin/w3s-pw-web-sdk',
        'undici': 'commonjs undici',
        'firebase': 'commonjs firebase',
        '@firebase/auth': 'commonjs @firebase/auth',
      });
    }
    
    return config;
  },
}

module.exports = nextConfig
