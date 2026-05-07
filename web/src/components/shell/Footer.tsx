"use client";

import React, { useState, FormEvent } from "react";

const NAV_LINKS = [
  { label: "Performance", href: "/performance" },
  { label: "Terminal", href: "/terminal" },
  { label: "Methodology", href: "/methodology" },
  { label: "Brief", href: "/brief" },
  { label: "About", href: "/about" },
];

const TRANSPARENCY_LINKS = [
  { label: "Methodology", href: "/methodology" },
  { label: "Performance", href: "/performance" },
];

export function Footer() {
  const [email, setEmail] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const url = new URL("https://fxregimelab.substack.com/");
    url.searchParams.set("utm_source", "website");
    url.searchParams.set("utm_campaign", "footer");
    if (email.trim()) {
      url.searchParams.set("email", email.trim());
    }
    window.open(url.toString(), "_blank", "noopener,noreferrer");
  };

  return (
    <footer className="border-t border-[#e5e5e5] bg-[#f5f5f0]">
      <div className="mx-auto max-w-[1440px] px-4 py-10">
        {/* 3-column grid */}
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {/* Column 1: Navigation */}
          <div>
            <h3 className="mb-3 text-[0.6875rem] font-semibold uppercase tracking-wider text-[#a8a29e]">
              Navigation
            </h3>
            <ul className="space-y-1.5">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className="text-[0.8125rem] text-[#57534e] outline-none transition-colors hover:text-[#0a0a0a] focus-visible:ring-2 focus-visible:ring-[#0a0a0a]"
                    style={{ borderRadius: 2 }}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 2: Transparency */}
          <div>
            <h3 className="mb-3 text-[0.6875rem] font-semibold uppercase tracking-wider text-[#a8a29e]">
              Transparency
            </h3>
            <ul className="space-y-1.5">
              {TRANSPARENCY_LINKS.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className="text-[0.8125rem] text-[#57534e] outline-none transition-colors hover:text-[#0a0a0a] focus-visible:ring-2 focus-visible:ring-[#0a0a0a]"
                    style={{ borderRadius: 2 }}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 3: Substack subscribe */}
          <div>
            <h3 className="mb-3 text-[0.6875rem] font-semibold uppercase tracking-wider text-[#a8a29e]">
              Subscribe
            </h3>
            <p className="mb-3 text-[0.8125rem] text-[#57534e]">
              Weekly regime briefs delivered to your inbox.
            </p>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="flex-1 border border-[#d6d3d1] bg-[#ffffff] px-3 py-2 text-[0.8125rem] text-[#0a0a0a] outline-none placeholder:text-[#a8a29e] focus-visible:ring-2 focus-visible:ring-[#0a0a0a]"
                style={{ borderRadius: 2 }}
                aria-label="Email address for Substack subscription"
              />
              <button
                type="submit"
                className="border border-[#0a0a0a] bg-[#0a0a0a] px-3 py-2 text-[0.8125rem] font-medium text-[#f5f5f0] outline-none transition-colors hover:bg-[#1c1917] focus-visible:ring-2 focus-visible:ring-[#0a0a0a] focus-visible:ring-offset-2"
                style={{ borderRadius: 2 }}
              >
                Subscribe
              </button>
            </form>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-10 border-t border-[#e5e5e5] pt-6">
          <p className="text-[0.75rem] text-[#a8a29e]">
            Research and learning only. Not investment advice.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
