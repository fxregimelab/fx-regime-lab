import React from 'react';

interface ValidationRow {
  date: string;
  pair: string;
  call: string;
  outcome: string;
  return_pct: number;
}

interface ValidationTableProps {
  rows: ValidationRow[];
  tone?: 'light' | 'dark';
}

export function ValidationTable({ rows, tone = 'light' }: ValidationTableProps) {
  const isD = tone === 'dark';
  const bg = isD ? '#0a0a0a' : '#fff';
  const border = isD ? '#1e1e1e' : '#e5e5e5';
  const hdr = isD ? '#888' : '#999';
  const text = isD ? '#ffffff' : '#111';
  const muted = isD ? '#aaa' : '#555';
  const stripe = isD ? '#0d0d0d' : '#fafafa';

  return (
    <div style={{ border: `1px solid ${border}`, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-jetbrains-mono)' }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${border}`, background: isD ? '#0d0d0d' : '#fafafa' }}>
            {['DATE', 'PAIR', 'CALL', 'OUTCOME', 'RET %'].map(h => (
              <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 10, color: hdr, letterSpacing: '0.1em', fontWeight: 600 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: i < rows.length - 1 ? `1px solid ${border}` : 'none', background: i % 2 === 1 ? stripe : bg }}>
              <td style={{ padding: '9px 16px', fontSize: 11, color: muted }}>{row.date}</td>
              <td style={{ padding: '9px 16px', fontSize: 11, color: text, fontWeight: 700 }}>{row.pair}</td>
              <td style={{ padding: '9px 16px', fontSize: 10, color: muted, maxWidth: 200 }}>{row.call}</td>
              <td style={{ padding: '9px 16px', fontSize: 11, fontWeight: 700, color: row.outcome === 'correct' ? '#16a34a' : '#dc2626' }}>
                {row.outcome === 'correct' ? '✓ correct' : '✗ incorrect'}
              </td>
              <td style={{ padding: '9px 16px', fontSize: 12, fontWeight: 700, color: row.return_pct >= 0 ? '#16a34a' : '#dc2626' }}>
                {row.return_pct >= 0 ? '+' : ''}{row.return_pct.toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
