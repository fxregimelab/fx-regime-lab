import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { NextConfig } from 'next';

const here = fileURLToPath(new URL('.', import.meta.url));

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  webpack: (config) => {
    const standalone = path.join(
      here,
      'node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.mjs'
    );
    config.resolve.alias = {
      ...config.resolve.alias,
      'lightweight-charts': standalone,
    };
    return config;
  },
};

export default nextConfig;
