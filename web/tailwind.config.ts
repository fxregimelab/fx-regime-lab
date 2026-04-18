import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'shell-bg': '#f5f5f0',
        'terminal-bg': '#0a0a0a',
        'terminal-surface': '#1a1a1a',
        accent: '#e8a045',
        /** Muted shell text; matches `globals.css` `--text-muted` for WCAG AA on shell-bg */
        muted: 'var(--text-muted)',
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['var(--font-fraunces)', 'ui-serif', 'Georgia', 'serif'],
        mono: ['var(--font-jetbrains-mono)', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        shell: '0.75rem',
        card: '1rem',
        pill: '9999px',
      },
    },
  },
  plugins: [],
};

export default config;
