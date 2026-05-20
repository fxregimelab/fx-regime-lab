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
    config.cache = false;
    config.resolve.symlinks = false;
    return config;
  },
};
export default config;
