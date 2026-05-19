import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import Link from "next/link";

const REPORTS_DIR = join(process.cwd(), "..", "pipeline", "reports");

interface Report {
  slug: string;
  title: string;
  content: string;
}

function parseMdTable(
  lines: string[],
): { headers: string[]; rows: string[][] } | null {
  const start = lines.findIndex((l) => l.startsWith("|"));
  if (start === -1) return null;
  const end = lines.slice(start).findIndex((l) => !l.trim().startsWith("|"));
  const tableLines =
    end === -1 ? lines.slice(start) : lines.slice(start, start + end);
  if (tableLines.length < 2) return null;

  const cells = (line: string) =>
    line
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());

  const headers = cells(tableLines[0]);
  const rows = tableLines.slice(2).map(cells);
  return { headers, rows };
}

function mdToHtml(md: string): string {
  const lines = md.split("\n");
  const out: string[] = [];
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trim = line.trim();

    if (trim.startsWith("# ")) {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      out.push(
        `<h1 class="font-sans text-2xl font-semibold tracking-tight mb-4">${escapeHtml(trim.slice(2))}</h1>`,
      );
      continue;
    }
    if (trim.startsWith("## ")) {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      out.push(
        `<h2 class="font-sans text-lg font-semibold tracking-tight mt-8 mb-3">${escapeHtml(trim.slice(3))}</h2>`,
      );
      continue;
    }
    if (trim.startsWith("- ")) {
      if (!inList) {
        out.push(
          '<ul class="list-disc list-inside space-y-1 mb-4 font-sans text-sm text-[var(--terminal-fg-muted)]">',
        );
        inList = true;
      }
      out.push(`<li>${escapeHtml(trim.slice(2))}</li>`);
      continue;
    }
    if (trim.startsWith("|")) {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      const table = parseMdTable(lines.slice(i));
      if (table) {
        out.push(
          '<div class="overflow-x-auto mb-6"><table class="w-full text-left border-collapse font-mono text-xs">',
        );
        out.push(
          `<thead><tr class="border-b border-[var(--terminal-border)]">${table.headers
            .map(
              (h) =>
                `<th class="py-2 pr-4 text-[var(--terminal-fg-muted)] uppercase tracking-widest">${escapeHtml(h)}</th>`,
            )
            .join("")}</tr></thead>`,
        );
        out.push(
          `<tbody>${table.rows
            .map(
              (row) =>
                `<tr class="border-b border-[var(--terminal-border-subtle)]">${row
                  .map(
                    (c) =>
                      `<td class="py-2 pr-4 text-[var(--terminal-fg)]">${escapeHtml(c)}</td>`,
                  )
                  .join("")}</tr>`,
            )
            .join("")}</tbody>`,
        );
        out.push("</table></div>");
        // Skip consumed lines
        const end = lines.slice(i).findIndex((l) => !l.trim().startsWith("|"));
        i += end === -1 ? lines.length - i - 1 : end - 1;
        continue;
      }
    }
    if (inList && !trim.startsWith("-")) {
      out.push("</ul>");
      inList = false;
    }
    if (trim === "") {
      out.push("<br/>");
      continue;
    }
    out.push(
      `<p class="font-sans text-sm text-[var(--terminal-fg-muted)] leading-relaxed mb-2">${escapeHtml(trim)}</p>`,
    );
  }
  if (inList) out.push("</ul>");
  return out.join("\n");
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function loadReports(): Report[] {
  try {
    const files = readdirSync(REPORTS_DIR).filter(
      (f) => f.startsWith("accuracy_comparison_") && f.endsWith(".md"),
    );
    return files.map((f) => {
      const content = readFileSync(join(REPORTS_DIR, f), "utf-8");
      const title = content.split("\n")[0].replace(/^#\s*/, "").trim();
      return { slug: f.replace(/\.md$/, ""), title: title || f, content };
    });
  } catch {
    return [];
  }
}

export const metadata = {
  title: "Diagnostics | FX Regime Lab",
};

export default function DiagnosticsPage() {
  const reports = loadReports();

  return (
    <main
      id="main-content"
      className="min-h-screen bg-[var(--color-void)] text-[var(--color-text-secondary)]"
    >
      <header className="border-b border-solid border-[var(--terminal-border)] bg-[var(--terminal-bg)] px-4 py-4">
        <Link
          href="/audit"
          className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] no-underline hover:text-[var(--terminal-fg-muted)]"
        >
          ← AUDIT
        </Link>
        <h1 className="mt-3 font-mono text-[11px] font-normal tracking-widest text-[var(--terminal-fg-muted)] tabular-nums">
          [ M.5 DIAGNOSTIC REPORTS ]
        </h1>
        <p className="mt-2 max-w-2xl font-mono text-[10px] leading-relaxed text-[var(--terminal-fg-dim)] tabular-nums">
          Accuracy comparisons and permutation importance from the simulation
          engine. Generated offline from the pipeline backtest suite.
        </p>
      </header>

      <div className="mx-auto max-w-4xl px-4 py-6">
        {reports.length === 0 ? (
          <div className="border border-solid border-[var(--terminal-border)] bg-[var(--terminal-bg)] p-6">
            <p className="font-mono text-[11px] text-[var(--terminal-fg-muted)]">
              No diagnostic reports found.
            </p>
            <p className="mt-2 font-mono text-[10px] text-[var(--terminal-fg-dim)]">
              Reports are generated by running{" "}
              <code className="text-[var(--terminal-fg-muted)]">
                python -m src.diagnostics.accuracy_report
              </code>{" "}
              in the pipeline directory. Output is written to{" "}
              <code className="text-[var(--terminal-fg-muted)]">
                pipeline/reports/
              </code>
              .
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {reports.map((report) => (
              <article
                key={report.slug}
                className="border border-solid border-[var(--terminal-border)] bg-[var(--terminal-bg)] p-6"
                id={report.slug}
              >
                {/* biome-ignore lint/security/noDangerouslySetInnerHtml: Trusted local markdown reports */}
                <div // biome-ignore lint/security/noDangerouslySetInnerHtml: Trusted local markdown reports
                  dangerouslySetInnerHTML={{ __html: mdToHtml(report.content) }}
                />
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
