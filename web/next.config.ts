import type { NextConfig } from "next";
const config: NextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  async redirects() {
    return [
      {
        source: "/performance",
        destination: "/track-record",
        permanent: true,
      },
    ];
  },
  webpack: (config) => {
    config.resolve.symlinks = false;
    // Persistent cache breaks on Windows with EISDIR errors
    config.cache = false;
    return config;
  },
};
export default config;
