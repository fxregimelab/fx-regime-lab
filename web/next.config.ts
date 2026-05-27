import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  poweredByHeader: false,
  generateEtags: true,
  images: {
    formats: ["image/webp", "image/avif"],
    minimumCacheTTL: 86400,
  },
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
