import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: "/terminal/",
    },
    sitemap: "https://fxregimelab.com/sitemap.xml",
  };
}
