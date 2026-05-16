#!/usr/bin/env node
/**
 * Lighthouse audit runner for FX Regime Lab.
 *
 * Usage:
 *   node scripts/lighthouse-audit.js
 *
 * Runs mobile + desktop audits against the production URL.
 * Saves JSON + HTML reports to lighthouse-reports/.
 * Exits with code 1 if any category score falls below threshold.
 */

const fs = require("fs");
const path = require("path");
const lighthouse = require("lighthouse");
const chromeLauncher = require("chrome-launcher");

const URL = process.env.LIGHTHOUSE_URL || "https://fxregimelab.com";
const REPORTS_DIR = path.join(__dirname, "..", "lighthouse-reports");

const THRESHOLDS = {
  mobile: {
    performance: 0.85,
    accessibility: 0.9,
    "best-practices": 0.9,
    seo: 0.9,
  },
  desktop: {
    performance: 0.9,
    accessibility: 0.9,
    "best-practices": 0.9,
    seo: 0.9,
  },
};

async function runAudit(device, chrome) {
  const options = {
    logLevel: "error",
    output: ["json", "html"],
    onlyCategories: ["performance", "accessibility", "best-practices", "seo"],
    port: chrome.port,
    formFactor: device,
    screenEmulation: {
      mobile: device === "mobile",
      width: device === "mobile" ? 390 : 1350,
      height: device === "mobile" ? 844 : 940,
      deviceScaleFactor: device === "mobile" ? 3 : 1,
      disabled: false,
    },
    emulatedUserAgent:
      device === "mobile"
        ? "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  };

  const runnerResult = await lighthouse(URL, options);
  const reportJson = runnerResult.report[0];
  const reportHtml = runnerResult.report[1];

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const baseName = `${timestamp}-${device}`;

  fs.mkdirSync(REPORTS_DIR, { recursive: true });
  fs.writeFileSync(path.join(REPORTS_DIR, `${baseName}.json`), reportJson);
  fs.writeFileSync(path.join(REPORTS_DIR, `${baseName}.html`), reportHtml);

  const scores = {};
  for (const cat of Object.keys(runnerResult.lhr.categories)) {
    scores[cat] = runnerResult.lhr.categories[cat].score;
  }

  return { device, scores, baseName };
}

async function main() {
  console.log(`Auditing ${URL} ...`);
  const chrome = await chromeLauncher.launch({ chromeFlags: ["--headless"] });

  let failed = false;
  try {
    for (const device of ["mobile", "desktop"]) {
      const result = await runAudit(device, chrome);
      console.log(`\n${device.toUpperCase()} results:`);
      const thresholds = THRESHOLDS[device];
      for (const [cat, score] of Object.entries(result.scores)) {
        const pct = Math.round((score || 0) * 100);
        const threshold = Math.round((thresholds[cat] || 0) * 100);
        const pass = (score || 0) >= (thresholds[cat] || 0);
        const icon = pass ? "✓" : "✗";
        console.log(`  ${icon} ${cat}: ${pct}% (threshold: ${threshold}%)`);
        if (!pass) failed = true;
      }
      console.log(`  Report: lighthouse-reports/${result.baseName}.html`);
    }
  } finally {
    await chrome.kill();
  }

  if (failed) {
    console.log("\n❌ Some scores fell below thresholds.");
    process.exit(1);
  } else {
    console.log("\n✅ All scores above thresholds.");
    process.exit(0);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
