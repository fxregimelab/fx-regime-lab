/**
 * Lighthouse CI configuration for FX Regime Lab.
 *
 * Targets:
 * - LCP < 1.5s on terminal pages
 * - INP < 100ms
 * - CLS < 0.05
 */
module.exports = {
  ci: {
    collect: {
      url: [
        "http://localhost:3000/",
        "http://localhost:3000/terminal",
        "http://localhost:3000/terminal/fx-regime",
        "http://localhost:3000/performance",
        "http://localhost:3000/methodology",
      ],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        "categories:performance": ["warn", { minScore: 0.85 }],
        "categories:accessibility": ["error", { minScore: 0.95 }],
        "categories:best-practices": ["warn", { minScore: 0.9 }],
        "categories:seo": ["warn", { minScore: 0.9 }],
        "largest-contentful-paint": ["warn", { maxNumericValue: 1500 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.05 }],
        "total-blocking-time": ["warn", { maxNumericValue: 100 }],
        interactive: ["warn", { maxNumericValue: 2500 }],
      },
    },
    upload: {
      target: "temporary-public-storage",
    },
  },
};
