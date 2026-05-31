/** @type {import('next').NextConfig} */
const internalApiUrl =
  process.env.INTERNAL_API_URL ||
  (process.env.INTERNAL_API_HOSTPORT ? `http://${process.env.INTERNAL_API_HOSTPORT}` : undefined);

const nextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || ""
  },
  async rewrites() {
    if (!internalApiUrl) {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiUrl}/api/:path*`
      }
    ];
  }
};

export default nextConfig;
