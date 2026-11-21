import { spawnSync } from "node:child_process";

// The parent gate runs this from pipeline/. No external services are started here.
const result = spawnSync("python", ["-m", "pytest", "-q", ...process.argv.slice(2)], {
  encoding: "utf8",
  timeout: 180_000,
  maxBuffer: 1024 * 1024,
  shell: false,
});
const output = `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
if (result.error || result.status !== 0 || !/\b[1-9]\d* passed\b/.test(output)) {
  process.stderr.write(output);
  if (result.error) process.stderr.write(`${result.error.message}\n`);
  process.exit(1);
}
process.stdout.write(output);
process.stdout.write("REPAIR_PYTEST_VERIFIED\n");
