/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  agentRules: false,
  async rewrites() {
    const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8011";
    return [
      { source: "/local-api/:path*", destination: `${backend}/api/:path*` },
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
    ];
  },
};
export default nextConfig;
