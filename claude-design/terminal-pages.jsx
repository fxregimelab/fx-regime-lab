
// ─── Terminal Index ───────────────────────────────────────────────────────────
function TerminalIndexPage({ navigate }) {
  return (
    <div style={{ minHeight: '100vh', background: '#080808', color: '#e8e8e8' }}>
      <TerminalNav currentRoute="/terminal" navigate={navigate} />
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 24px' }}>

        {/* Cross-pair overview ticker */}
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)`, gap: 2, marginBottom: 32 }}>
          {PAIRS.map((p) => {
            const call = MOCK_REGIME_CALLS[p.label];
            const sig = MOCK_SIGNALS[p.label];
            const chg = sig?.day_change_pct;
            return (
              <button key={p.label} onClick={() => navigate(`/terminal/fx-regime/${p.urlSlug}`)}
                style={{ background: '#0d0d0d', border: `1px solid #1e1e1e`, borderTop: `2px solid ${p.pairColor}`, padding: '16px 18px', textAlign: 'left', transition: 'background 0.1s', cursor: 'pointer' }}
                onMouseEnter={e => e.currentTarget.style.background = '#111'}
                onMouseLeave={e => e.currentTarget.style.background = '#0d0d0d'}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: p.pairColor, fontWeight: 700, letterSpacing: '0.04em' }}>{p.display}</span>
                  {chg != null && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: chg >= 0 ? '#4ade80' : '#f87171' }}>{chg >= 0 ? '+' : ''}{chg.toFixed(2)}%</span>}
                </div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 26, fontWeight: 700, color: '#ffffff', letterSpacing: '-0.03em', lineHeight: 1, marginBottom: 6 }}>
                  {sig?.spot?.toFixed(p.label === 'USDJPY' ? 2 : 4) ?? '—'}
                </p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 700, color: '#c0c0c0', letterSpacing: '0.03em', marginBottom: 10 }}>
                  {call?.regime ?? '—'}
                </p>
                <ConfidenceBar value={call?.confidence} tone="dark" color={p.pairColor} />
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555', marginTop: 5, letterSpacing: '0.06em' }}>CONF {fmtPct(call?.confidence)}</p>
              </button>
            );
          })}
        </div>

        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#666', letterSpacing: '0.12em', marginBottom: 12 }}>STRATEGIES</p>

        <div style={{ border: '1px solid #1e1e1e', cursor: 'pointer' }}
          onClick={() => navigate('/terminal/fx-regime')}
          onMouseEnter={e => e.currentTarget.style.borderColor = '#2a2a2a'}
          onMouseLeave={e => e.currentTarget.style.borderColor = '#1e1e1e'}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #1a1a1a', display: 'flex', justifyContent: 'space-between', background: '#0c0c0c' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em' }}>ACTIVE STRATEGY</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: BRAND.accent, fontWeight: 700 }}>FX-REGIME</span>
            </div>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#666' }}>Open →</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)`, borderBottom: '1px solid #141414' }}>
            {PAIRS.map((p, i) => {
              const call = MOCK_REGIME_CALLS[p.label];
              return (
                <div key={p.label} style={{ padding: '16px 20px', borderRight: i < 2 ? '1px solid #141414' : 'none' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: p.pairColor, fontWeight: 700, marginBottom: 6 }}>{p.display}</p>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#c0c0c0', fontWeight: 700, letterSpacing: '0.03em', marginBottom: 8 }}>{call?.regime ?? '—'}</p>
                  <div style={{ display: 'flex', gap: 16 }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#999' }}>CONF <span style={{ color: '#e0e0e0', fontWeight: 700 }}>{fmtPct(call?.confidence)}</span></span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#666' }}>COMPOSITE <span style={{ color: '#e0e0e0', fontWeight: 700 }}>{fmt2(call?.signal_composite)}</span></span>
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#4ade80' }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#777' }}>Pipeline: {TODAY} 07:12 UTC</span>
          </div>
        </div>

        <div style={{ border: '1px dashed #141414', marginTop: 2, padding: '14px 20px' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#222', letterSpacing: '0.1em' }}>MORE STRATEGIES — PHASE 2+</span>
        </div>
      </div>
    </div>
  );
}

// ─── Terminal Strategy Page ───────────────────────────────────────────────────
function TerminalStrategyPage({ navigate }) {
  return (
    <div style={{ minHeight: '100vh', background: '#080808', color: '#e8e8e8' }}>
      <TerminalNav currentRoute="/terminal/fx-regime" navigate={navigate} />
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 24px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#666', letterSpacing: '0.12em', marginBottom: 8 }}>FX-REGIME · SELECT PAIR DESK</p>
        <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 20, color: '#f0f0f0', letterSpacing: '-0.02em', marginBottom: 32 }}>Pair desks</h1>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, background: '#141414', border: '1px solid #141414' }}>
          {PAIRS.map(p => {
            const call = MOCK_REGIME_CALLS[p.label];
            const sig = MOCK_SIGNALS[p.label];
            const chg = sig?.day_change_pct;
            return (
              <div key={p.label} onClick={() => navigate(`/terminal/fx-regime/${p.urlSlug}`)}
                style={{ background: '#0a0a0a', padding: '22px', cursor: 'pointer', borderTop: `3px solid ${p.pairColor}`, transition: 'background 0.1s' }}
                onMouseEnter={e => e.currentTarget.style.background = '#0f0f0f'}
                onMouseLeave={e => e.currentTarget.style.background = '#0a0a0a'}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: p.pairColor, fontWeight: 700 }}>{p.display}</p>
                  {chg != null && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: chg >= 0 ? '#4ade80' : '#f87171', fontWeight: 700 }}>{chg >= 0 ? '+' : ''}{chg.toFixed(2)}%</span>}
                </div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 28, fontWeight: 700, color: '#fff', letterSpacing: '-0.03em', lineHeight: 1, marginBottom: 10 }}>
                  {sig?.spot?.toFixed(p.label === 'USDJPY' ? 2 : 4) ?? '—'}
                </p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 700, color: '#bbb', letterSpacing: '0.03em', marginBottom: 12, lineHeight: 1.4 }}>{call?.regime ?? '—'}</p>
                <div style={{ marginBottom: 14 }}>
                  <ConfidenceBar value={call?.confidence} tone="dark" color={p.pairColor} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#666', letterSpacing: '0.1em' }}>CONFIDENCE</span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', fontWeight: 700 }}>{fmtPct(call?.confidence)}</span>
                  </div>
                </div>
                <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {[['RATE DIFF 2Y', fmt2(sig?.rate_diff_2y)], ['COT PCT', fmtInt(sig?.cot_percentile)], ['RVOL 20D', fmt2(sig?.realized_vol_20d)], ['COMPOSITE', fmt2(call?.signal_composite)]].map(([lbl, val]) => (
                    <div key={lbl} style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.06em' }}>{lbl}</span>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#e8e8e8', fontWeight: 700 }}>{val}</span>
                    </div>
                  ))}
                </div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333', marginTop: 14, letterSpacing: '0.08em' }}>OPEN DESK →</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── AI Analysis Panel ────────────────────────────────────────────────────────
function AiAnalysisPanel({ pair, call, sig }) {
  const [analysis, setAnalysis] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const prompt = `You are a professional FX macro analyst. Analyze ${pair.display} using this current data:

Regime: ${call?.regime}
Confidence: ${Math.round((call?.confidence ?? 0) * 100)}%
Signal Composite: ${call?.signal_composite?.toFixed(2)}
Rate Differential 2Y: ${sig?.rate_diff_2y?.toFixed(2)}
COT Percentile: ${sig?.cot_percentile}
Realized Vol 20D: ${sig?.realized_vol_20d?.toFixed(2)}
Realized Vol 5D: ${sig?.realized_vol_5d?.toFixed(2)}
Implied Vol 30D: ${sig?.implied_vol_30d?.toFixed(2) ?? 'N/A'}
Spot: ${sig?.spot?.toFixed(4)}
Primary Driver: ${call?.primary_driver}

Provide a concise structured response in this EXACT format:

OUTLOOK
[2-3 sentences on near-term directional view for ${pair.display}]

KEY RISKS
• [Risk 1]
• [Risk 2]
• [Risk 3]

SCENARIOS
BULL (X%): [what happens and why]
BASE (X%): [what happens and why]
BEAR (X%): [what happens and why]

WATCH LEVELS
• [Key level 1 with brief note]
• [Key level 2 with brief note]

Keep probabilities realistic and sum to ~100%. Be specific, analytical, no fluff.`;

      const text = await window.claude.complete(prompt);
      setAnalysis(text);
    } catch (e) {
      setError('AI generation failed. Please try again.');
    }
    setLoading(false);
  };

  // Parse sections
  const parseAnalysis = (text) => {
    const sections = {};
    const parts = text.split(/\n(?=OUTLOOK|KEY RISKS|SCENARIOS|WATCH LEVELS)/);
    parts.forEach(part => {
      const lines = part.trim().split('\n');
      const header = lines[0].trim();
      const body = lines.slice(1).join('\n').trim();
      if (header && body) sections[header] = body;
    });
    return sections;
  };

  // Parse scenarios for probability display
  const parseScenarios = (text) => {
    const scenarios = [];
    const lines = text.split('\n');
    lines.forEach(line => {
      const m = line.match(/^(BULL|BASE|BEAR)\s*\((\d+)%\):\s*(.+)/i);
      if (m) {
        scenarios.push({
          type: m[1].toUpperCase(),
          prob: parseInt(m[2]),
          desc: m[3].trim(),
          color: m[1].toUpperCase() === 'BULL' ? '#4ade80' : m[1].toUpperCase() === 'BEAR' ? '#f87171' : '#fbbf24'
        });
      }
    });
    return scenarios;
  };

  if (!analysis && !loading) {
    return (
      <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', borderTop: `2px solid ${pair.pairColor}` }}>
        <div style={{ padding: '16px 18px', borderBottom: '1px solid #141414', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 6, height: 6, background: pair.pairColor, display: 'inline-block' }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em' }}>AI ANALYTICS</span>
          </div>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>claude-haiku</span>
        </div>
        <div style={{ padding: '20px 18px', textAlign: 'center' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#444', marginBottom: 14, lineHeight: 1.7 }}>
            Generate AI analysis for {pair.display} based on current regime signals, confidence, and composite score.
          </p>
          <button onClick={generate}
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: pair.pairColor, border: `1px solid ${pair.pairColor}40`, background: `${pair.pairColor}10`, padding: '8px 18px', cursor: 'pointer', letterSpacing: '0.06em', fontWeight: 700, width: '100%' }}>
            ✦ GENERATE ANALYSIS
          </button>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#222', marginTop: 10 }}>Outlook · Risks · Probabilities · Levels</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', borderTop: `2px solid ${pair.pairColor}` }}>
        <div style={{ padding: '16px 18px', borderBottom: '1px solid #141414', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 6, height: 6, background: pair.pairColor, display: 'inline-block' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em' }}>AI ANALYTICS — GENERATING</span>
        </div>
        <div style={{ padding: '24px 18px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', gap: 4 }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 6, height: 6, background: pair.pairColor,
                animation: `pulse 1.2s ${i * 0.2}s infinite`,
                opacity: 0.6
              }} />
            ))}
          </div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#444' }}>Analyzing {pair.display} signals...</p>
        </div>
        <style>{`@keyframes pulse { 0%,100%{opacity:0.2;transform:scaleY(1)} 50%{opacity:1;transform:scaleY(1.4)} }`}</style>
      </div>
    );
  }

  const sections = parseAnalysis(analysis);
  const scenariosText = sections['SCENARIOS'] ?? '';
  const scenarios = parseScenarios(scenariosText);

  return (
    <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', borderTop: `2px solid ${pair.pairColor}` }}>
      <div style={{ padding: '12px 14px', borderBottom: '1px solid #141414', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 6, height: 6, background: pair.pairColor, display: 'inline-block' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em' }}>AI ANALYTICS · {pair.display}</span>
        </div>
        <button onClick={() => { setAnalysis(null); }}
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333', background: 'none', cursor: 'pointer', letterSpacing: '0.08em' }}>↺ REDO</button>
      </div>

      {/* Outlook */}
      {sections['OUTLOOK'] && (
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #111' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555', letterSpacing: '0.12em', marginBottom: 6 }}>OUTLOOK</p>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#aaa', lineHeight: 1.65 }}>{sections['OUTLOOK']}</p>
        </div>
      )}

      {/* Scenarios with prob bars */}
      {scenarios.length > 0 && (
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #111' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555', letterSpacing: '0.12em', marginBottom: 10 }}>SCENARIOS</p>
          {scenarios.map((s, i) => (
            <div key={i} style={{ marginBottom: i < scenarios.length - 1 ? 12 : 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: s.color, fontWeight: 700, letterSpacing: '0.06em' }}>{s.type}</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: s.color, fontWeight: 700 }}>{s.prob}%</span>
              </div>
              <div style={{ background: '#141414', height: 3, marginBottom: 5 }}>
                <div style={{ width: `${s.prob}%`, height: '100%', background: s.color, opacity: 0.7 }} />
              </div>
              <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#555', lineHeight: 1.5 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      )}

      {/* Key Risks */}
      {sections['KEY RISKS'] && (
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #111' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555', letterSpacing: '0.12em', marginBottom: 8 }}>KEY RISKS</p>
          {sections['KEY RISKS'].split('\n').filter(l => l.trim().startsWith('•') || l.trim().startsWith('-')).map((l, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 5 }}>
              <span style={{ color: '#f87171', fontFamily: 'JetBrains Mono, monospace', fontSize: 9, flexShrink: 0, marginTop: 1 }}>▸</span>
              <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#666', lineHeight: 1.5 }}>{l.replace(/^[•\-]\s*/, '')}</p>
            </div>
          ))}
        </div>
      )}

      {/* Watch Levels */}
      {sections['WATCH LEVELS'] && (
        <div style={{ padding: '12px 14px' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555', letterSpacing: '0.12em', marginBottom: 8 }}>WATCH LEVELS</p>
          {sections['WATCH LEVELS'].split('\n').filter(l => l.trim().startsWith('•') || l.trim().startsWith('-')).map((l, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 5 }}>
              <span style={{ color: pair.pairColor, fontFamily: 'JetBrains Mono, monospace', fontSize: 9, flexShrink: 0, marginTop: 1 }}>→</span>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#777', lineHeight: 1.5 }}>{l.replace(/^[•\-]\s*/, '')}</p>
            </div>
          ))}
        </div>
      )}

      {error && <p style={{ padding: '10px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#f87171' }}>{error}</p>}
    </div>
  );
}

// ─── Pair Calendar Widget (sidebar) ──────────────────────────────────────────
function PairCalendarWidget({ pair }) {
  const impactColor = (impact) => impact === 'HIGH' ? '#D94030' : '#F5923A';
  const today = new Date(TODAY);

  const events = MOCK_CALENDAR
    .filter(e => e.pairs.includes(pair.label))
    .sort((a, b) => a.date.localeCompare(b.date));

  const daysUntil = (dateStr) => Math.ceil((new Date(dateStr) - today) / 86400000);

  if (!events.length) {
    return (
      <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', padding: '14px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em', marginBottom: 8 }}>UPCOMING EVENTS</p>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>No events in calendar for this pair.</p>
      </div>
    );
  }

  return (
    <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c' }}>
      <div style={{ padding: '12px 14px', borderBottom: '1px solid #141414', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em' }}>UPCOMING EVENTS</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>{events.length} ahead</span>
      </div>
      <div>
        {events.slice(0, 4).map((e, i) => {
          const days = daysUntil(e.date);
          const dateObj = new Date(e.date + 'T00:00:00Z');
          const dayStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
          return (
            <div key={i} style={{ padding: '10px 14px', borderBottom: i < Math.min(events.length, 4) - 1 ? '1px solid #0f0f0f' : 'none', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <div style={{ width: 3, height: '100%', background: impactColor(e.impact), flexShrink: 0, marginTop: 3, alignSelf: 'stretch' }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#aaa', fontWeight: 600, lineHeight: 1.3, marginBottom: 3, textWrap: 'pretty' }}>{e.event}</p>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444' }}>{dayStr}</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fontWeight: 700, color: days <= 2 ? '#D94030' : days <= 7 ? '#F5923A' : '#333' }}>
                    {days === 0 ? 'TODAY' : days === 1 ? 'TOMORROW' : `${days}d`}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Calendar Tab Content (main panel) ───────────────────────────────────────
function PairCalendarTab({ pair, navigate }) {
  const [expandedEvent, setExpandedEvent] = React.useState(null);
  const [aiBriefs, setAiBriefs] = React.useState({});
  const [aiLoading, setAiLoading] = React.useState({});

  const impactColor = (impact) => impact === 'HIGH' ? '#D94030' : impact === 'MEDIUM' ? '#F5923A' : '#888';
  const today = new Date(TODAY);
  const daysUntil = (dateStr) => Math.ceil((new Date(dateStr) - today) / 86400000);

  const events = MOCK_CALENDAR
    .filter(e => e.pairs.includes(pair.label))
    .sort((a, b) => a.date.localeCompare(b.date));

  const generateBrief = async (e) => {
    const key = `${e.date}-${e.event}`;
    if (aiBriefs[key] || aiLoading[key]) return;
    setAiLoading(prev => ({ ...prev, [key]: true }));

    const pairNames = e.pairs.map(lbl => PAIRS.find(p => p.label === lbl)?.display).filter(Boolean).join(', ');
    const call = MOCK_REGIME_CALLS[pair.label];

    try {
      const prompt = `You are an FX macro analyst. Provide a structured brief for this economic event:

Event: ${e.event}
Date: ${e.date}
Impact: ${e.impact}
Relevant pairs: ${pairNames}
Current ${pair.display} regime: ${call?.regime} (${Math.round((call?.confidence ?? 0) * 100)}% confidence)

Respond in this EXACT format:

WHAT IT IS
[1-2 sentences explaining this event simply]

MARKET EXPECTATIONS
[Specific consensus expectations — include numbers/forecasts if applicable. E.g. "Consensus expects X% vs prior Y%"]

WHY IT MATTERS FOR ${pair.display.toUpperCase()}
[2-3 sentences on the FX impact mechanism, specifically for this pair]

SCENARIOS
BEAT (X%): [outcome for ${pair.display} if data beats expectations]
IN LINE (X%): [outcome if data meets expectations]
MISS (X%): [outcome if data misses expectations]

Keep probabilities realistic. Be specific, analytical, no fluff.`;

      const text = await window.claude.complete(prompt);
      setAiBriefs(prev => ({ ...prev, [key]: text }));
    } catch {
      setAiBriefs(prev => ({ ...prev, [key]: 'ERROR: Could not generate brief.' }));
    }
    setAiLoading(prev => ({ ...prev, [key]: false }));
  };

  const handleExpand = (e) => {
    const key = `${e.date}-${e.event}`;
    const isOpen = expandedEvent === key;
    setExpandedEvent(isOpen ? null : key);
    if (!isOpen && !aiBriefs[key]) {
      generateBrief(e);
    }
  };

  if (!events.length) {
    return (
      <div style={{ border: '1px solid #1a1a1a', borderTop: 'none', padding: '32px 20px', textAlign: 'center' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#333' }}>No calendar events for {pair.display}.</p>
      </div>
    );
  }

  const parseEventBrief = (text) => {
    const sections = {};
    const parts = text.split(/\n(?=WHAT IT IS|MARKET EXPECTATIONS|WHY IT MATTERS|SCENARIOS)/);
    parts.forEach(part => {
      const lines = part.trim().split('\n');
      const header = lines[0].trim();
      const body = lines.slice(1).join('\n').trim();
      if (header) sections[header] = body;
    });
    return sections;
  };

  const parseEventScenarios = (text) => {
    const scenarios = [];
    text.split('\n').forEach(line => {
      const m = line.match(/^(BEAT|IN LINE|MISS)\s*\((\d+)%\):\s*(.+)/i);
      if (m) scenarios.push({ type: m[1].toUpperCase(), prob: parseInt(m[2]), desc: m[3].trim() });
    });
    return scenarios;
  };

  return (
    <div style={{ border: '1px solid #1a1a1a', borderTop: 'none' }}>
      <div style={{ padding: '12px 18px', borderBottom: '1px solid #141414', background: '#0c0c0c', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em' }}>MACRO CALENDAR · {pair.display} EVENTS</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444' }}>{events.length} upcoming · click for AI brief</span>
      </div>

      {events.map((e, i) => {
        const key = `${e.date}-${e.event}`;
        const isOpen = expandedEvent === key;
        const days = daysUntil(e.date);
        const dateObj = new Date(e.date + 'T00:00:00Z');
        const dayStr = dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' });
        const brief = aiBriefs[key];
        const briefLoading = aiLoading[key];
        const sections = brief ? parseEventBrief(brief) : {};
        const scenariosText = sections['SCENARIOS'] ?? '';
        const scenarios = parseEventScenarios(scenariosText);
        const impactPairs = e.pairs.map(lbl => PAIRS.find(p => p.label === lbl));

        return (
          <div key={key} style={{ borderBottom: i < events.length - 1 ? '1px solid #0f0f0f' : 'none' }}>
            {/* Event header row */}
            <button onClick={() => handleExpand(e)}
              style={{ width: '100%', display: 'grid', gridTemplateColumns: '4px 80px 1fr auto auto', gap: 14, alignItems: 'center', padding: '14px 18px', background: isOpen ? '#0e0e0e' : 'transparent', cursor: 'pointer', textAlign: 'left', transition: 'background 0.1s' }}
              onMouseEnter={ev => { if (!isOpen) ev.currentTarget.style.background = '#0d0d0d'; }}
              onMouseLeave={ev => { if (!isOpen) ev.currentTarget.style.background = 'transparent'; }}>

              {/* Impact bar */}
              <div style={{ background: impactColor(e.impact), height: '100%', minHeight: 36, width: 3, alignSelf: 'stretch' }} />

              {/* Date */}
              <div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444', letterSpacing: '0.06em', marginBottom: 2 }}>{dayStr}</p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fontWeight: 700, color: days <= 2 ? '#D94030' : days <= 7 ? '#F5923A' : '#333' }}>
                  {days === 0 ? 'TODAY' : days === 1 ? 'TMRW' : `${days}d`}
                </p>
              </div>

              {/* Event name */}
              <div>
                <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#ccc', fontWeight: 600, marginBottom: 3 }}>{e.event}</p>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#444', letterSpacing: '0.08em' }}>{e.category}</span>
                  {impactPairs.filter(Boolean).map(pm => (
                    <span key={pm.label} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: pm.pairColor }}>· {pm.display}</span>
                  ))}
                </div>
              </div>

              {/* Impact badge */}
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: impactColor(e.impact), fontWeight: 700, letterSpacing: '0.08em', whiteSpace: 'nowrap' }}>{e.impact}</span>

              {/* AI / expand indicator */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {brief && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#4ade80' }}>✦ AI</span>}
                {briefLoading && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555' }}>...</span>}
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#333', transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s', display: 'inline-block' }}>›</span>
              </div>
            </button>

            {/* Expanded AI Brief */}
            {isOpen && (
              <div style={{ background: '#0a0a0a', borderTop: '1px solid #141414', padding: '0' }}>
                {briefLoading && (
                  <div style={{ padding: '20px 32px', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ display: 'flex', gap: 3 }}>
                      {[0,1,2].map(i => (
                        <div key={i} style={{ width: 5, height: 5, background: BRAND.accent, opacity: 0.5, animation: `pulse 1.2s ${i*0.2}s infinite` }} />
                      ))}
                    </div>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#444' }}>Generating AI brief for {e.event}...</span>
                  </div>
                )}

                {brief && !briefLoading && (
                  <div style={{ padding: '18px 32px 20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>

                    {/* Left col: What it is + Why it matters */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                      {sections['WHAT IT IS'] && (
                        <div>
                          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555', letterSpacing: '0.12em', marginBottom: 6 }}>WHAT IT IS</p>
                          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#888', lineHeight: 1.65 }}>{sections['WHAT IT IS']}</p>
                        </div>
                      )}
                      {sections['MARKET EXPECTATIONS'] && (
                        <div style={{ background: '#0e0e0e', border: '1px solid #1a1a1a', padding: '12px 14px' }}>
                          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: BRAND.accent, letterSpacing: '0.12em', marginBottom: 6 }}>MARKET EXPECTATIONS</p>
                          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#aaa', lineHeight: 1.65 }}>{sections['MARKET EXPECTATIONS']}</p>
                        </div>
                      )}
                      {(() => {
                        const whyKey = Object.keys(sections).find(k => k.startsWith('WHY IT MATTERS'));
                        return whyKey && sections[whyKey] ? (
                          <div>
                            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555', letterSpacing: '0.12em', marginBottom: 6 }}>WHY IT MATTERS FOR {pair.display}</p>
                            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#666', lineHeight: 1.65 }}>{sections[whyKey]}</p>
                          </div>
                        ) : null;
                      })()}
                    </div>

                    {/* Right col: Scenarios */}
                    <div>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555', letterSpacing: '0.12em', marginBottom: 10 }}>SCENARIOS FOR {pair.display}</p>
                      {scenarios.length > 0 ? scenarios.map((s, si) => {
                        const scenColor = s.type === 'BEAT' ? '#4ade80' : s.type === 'MISS' ? '#f87171' : '#fbbf24';
                        return (
                          <div key={si} style={{ marginBottom: 14 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
                              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: scenColor, fontWeight: 700 }}>{s.type}</span>
                              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: scenColor, fontWeight: 700 }}>{s.prob}%</span>
                            </div>
                            <div style={{ background: '#141414', height: 3, marginBottom: 6 }}>
                              <div style={{ width: `${s.prob}%`, height: '100%', background: scenColor, opacity: 0.8 }} />
                            </div>
                            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#555', lineHeight: 1.5 }}>{s.desc}</p>
                          </div>
                        );
                      }) : (
                        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#333', lineHeight: 1.7 }}>{scenariosText}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
      <style>{`@keyframes pulse { 0%,100%{opacity:0.2} 50%{opacity:1} }`}</style>
    </div>
  );
}

// ─── Terminal Pair Desk ───────────────────────────────────────────────────────
function TerminalPairDeskPage({ pairSlug, navigate }) {
  const pair = PAIRS.find(p => p.urlSlug === pairSlug) ?? PAIRS[0];
  const call = MOCK_REGIME_CALLS[pair.label];
  const sig = MOCK_SIGNALS[pair.label];
  const history = MOCK_HISTORY[pair.label] ?? [];

  const [activeTab, setActiveTab] = React.useState('signals');
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);

  const regimeAccent = call && call.confidence >= 0.55 &&
    (call.regime.includes('STRENGTH') || call.regime.includes('WEAKNESS') || call.regime.includes('PRESSURE') || call.regime === 'VOL_EXPANDING');

  const cotPct = sig?.cot_percentile;
  const crowding = cotPct != null ? (cotPct > 85 ? 'EXTREME HIGH' : cotPct < 15 ? 'EXTREME LOW' : null) : null;
  const rateArrow = rs => rs === 'BULLISH' ? '↑' : rs === 'BEARISH' ? '↓' : '→';
  const chg = sig?.day_change_pct;
  const composite = call?.signal_composite ?? 0;
  const compPct = Math.min(100, Math.max(0, ((composite + 2) / 4) * 100));

  const TABS = ['signals', 'history', 'charts', 'attribution', 'calendar', 'ai'];

  return (
    <div style={{ minHeight: '100vh', background: '#080808', color: '#e8e8e8' }}>
      <TerminalNav currentRoute={`/terminal/fx-regime/${pairSlug}`} navigate={navigate} />

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>

        {/* ── Top strip: spot + regime + confidence + composite ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 2, marginBottom: 2, border: '1px solid #1e1e1e' }}>
          <div style={{ background: '#0d0d0d', padding: '18px 20px', borderRight: '1px solid #1a1a1a' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555', letterSpacing: '0.12em', marginBottom: 6 }}>SPOT PRICE</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 30, fontWeight: 700, color: '#fff', letterSpacing: '-0.03em', lineHeight: 1 }}>
              {sig?.spot?.toFixed(pair.label === 'USDJPY' ? 2 : 4) ?? '—'}
            </p>
            {chg != null && (
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: chg >= 0 ? '#4ade80' : '#f87171', marginTop: 6 }}>
                {chg >= 0 ? '+' : ''}{chg.toFixed(2)}% today
              </p>
            )}
          </div>
          <div style={{ background: '#0d0d0d', padding: '18px 20px', borderRight: '1px solid #1a1a1a' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555', letterSpacing: '0.12em', marginBottom: 6 }}>REGIME</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: regimeAccent ? BRAND.accent : '#ffffff', letterSpacing: '0.02em', lineHeight: 1.4 }}>
              {call?.regime ?? '—'}
            </p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888', marginTop: 8 }}>{call?.primary_driver?.slice(0, 45)}…</p>
          </div>
          <div style={{ background: '#0d0d0d', padding: '18px 20px', borderRight: '1px solid #1a1a1a' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555', letterSpacing: '0.12em', marginBottom: 6 }}>CONFIDENCE</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 36, fontWeight: 700, color: pair.pairColor, letterSpacing: '-0.04em', lineHeight: 1 }}>
              {call ? Math.round(call.confidence * 100) : '—'}<span style={{ fontSize: 16, color: '#444', fontWeight: 400 }}>{call ? '%' : ''}</span>
            </p>
            <div style={{ marginTop: 8 }}><ConfidenceBar value={call?.confidence} tone="dark" color={pair.pairColor} /></div>
          </div>
          <div style={{ background: '#0d0d0d', padding: '18px 20px' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555', letterSpacing: '0.12em', marginBottom: 6 }}>COMPOSITE SCORE</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 36, fontWeight: 700, color: composite >= 0 ? '#4ade80' : '#f87171', letterSpacing: '-0.04em', lineHeight: 1 }}>
              {composite >= 0 ? '+' : ''}{fmt2(call?.signal_composite)}
            </p>
            <div style={{ marginTop: 8, background: '#1a1a1a', height: 3, position: 'relative' }}>
              <div style={{ position: 'absolute', left: '50%', top: -1, width: 1, height: 5, background: '#333' }} />
              <div style={{ width: `${compPct}%`, height: '100%', background: composite >= 0 ? '#4ade80' : '#f87171' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#333' }}>BEAR -2</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#333' }}>BULL +2</span>
            </div>
          </div>
        </div>

        {/* ── Signal chips ── */}
        <div style={{ background: '#0c0c0c', border: '1px solid #1a1a1a', borderTop: 'none', padding: '10px 20px', display: 'flex', gap: 8, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#666', letterSpacing: '0.1em', marginRight: 4 }}>SIGNALS:</span>
          {[
            ['RATE', call?.rate_signal, call?.rate_signal === 'BULLISH' ? '#4ade80' : call?.rate_signal === 'BEARISH' ? '#f87171' : '#888'],
            ['COT', cotPct != null ? (cotPct > 60 ? 'BULLISH' : cotPct < 40 ? 'BEARISH' : 'NEUTRAL') : null, cotPct > 60 ? '#4ade80' : cotPct < 40 ? '#f87171' : '#888'],
            ['VOL', sig?.realized_vol_20d != null ? (sig.realized_vol_20d > 8 ? 'ELEVATED' : 'NORMAL') : null, sig?.realized_vol_20d > 8 ? '#fbbf24' : '#4ade80'],
            ['IV', sig?.implied_vol_30d != null ? (sig.implied_vol_30d > sig.realized_vol_20d ? 'IV>RV' : 'IV<RV') : null, sig?.implied_vol_30d > sig?.realized_vol_20d ? '#fbbf24' : '#888'],
          ].filter(([, d]) => d).map(([lbl, dir, color]) => (
            <span key={lbl} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '4px 10px', color, border: `1px solid ${color}30`, background: `${color}10`, letterSpacing: '0.05em', fontWeight: 700 }}>
              {lbl}: {dir}
            </span>
          ))}
          {crowding && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '4px 10px', color: '#fbbf24', border: '1px solid #fbbf2430', background: '#fbbf2410', fontWeight: 700 }}>COT: {crowding}</span>}
          {/* Pair calendar events badge */}
          {(() => {
            const upcoming = MOCK_CALENDAR.filter(e => e.pairs.includes(pair.label) && e.impact === 'HIGH');
            const nextHigh = upcoming.sort((a, b) => a.date.localeCompare(b.date))[0];
            if (!nextHigh) return null;
            const days = Math.ceil((new Date(nextHigh.date) - new Date(TODAY)) / 86400000);
            return (
              <span onClick={() => setActiveTab('calendar')}
                style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '4px 10px', color: '#D94030', border: '1px solid #D9403030', background: '#D9403010', fontWeight: 700, cursor: 'pointer', letterSpacing: '0.04em' }}>
                ⚑ HIGH EVENT {days <= 1 ? 'TOMORROW' : `IN ${days}D`}
              </span>
            );
          })()}
          <span style={{ marginLeft: 'auto', fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>{TODAY} 07:12 UTC</span>
        </div>

        {/* ── Main grid: left panel + right sidebar ── */}
        <div style={{ display: 'grid', gridTemplateColumns: sidebarCollapsed ? '1fr 44px' : '1fr 300px', gap: 2, transition: 'grid-template-columns 0.25s ease' }}>

          {/* ─ Left panel ─ */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>

            {/* Tabs */}
            <div style={{ display: 'flex', background: '#0a0a0a', borderBottom: '1px solid #1a1a1a', flexWrap: 'wrap' }}>
              {TABS.map(tab => {
                const isAi = tab === 'ai';
                const isCal = tab === 'calendar';
                return (
                  <button key={tab} onClick={() => setActiveTab(tab)}
                    style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: '0.12em', padding: '11px 16px', color: activeTab === tab ? (isAi ? BRAND.accent : isCal ? '#fbbf24' : '#f0f0f0') : '#3a3a3a', borderBottom: activeTab === tab ? `2px solid ${isAi ? BRAND.accent : isCal ? '#fbbf24' : pair.pairColor}` : '2px solid transparent', transition: 'color 0.1s', marginBottom: -1, background: activeTab === tab ? '#0d0d0d' : 'transparent', display: 'flex', alignItems: 'center', gap: 5 }}>
                    {isAi && <span style={{ fontSize: 8 }}>✦</span>}
                    {isCal && <span style={{ fontSize: 8 }}>⚑</span>}
                    {tab.toUpperCase()}
                  </button>
                );
              })}
            </div>

            {/* SIGNALS tab */}
            {activeTab === 'signals' && (
              <div style={{ border: '1px solid #1a1a1a', borderTop: 'none' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'JetBrains Mono, monospace' }}>
                  <thead>
                    <tr style={{ background: '#0c0c0c', borderBottom: '1px solid #1a1a1a' }}>
                      {['SIGNAL', 'VALUE', 'DIR', 'NOTE'].map(h => (
                        <th key={h} style={{ padding: '9px 18px', textAlign: 'left', fontSize: 9, color: '#777', letterSpacing: '0.12em', fontWeight: 600 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ['Rate differential 2Y', fmt2(sig?.rate_diff_2y), rateArrow(call?.rate_signal), call?.rate_signal ?? ''],
                      ['COT net position pctile', fmtInt(cotPct ?? null), cotPct > 60 ? '↑' : cotPct < 40 ? '↓' : '→', crowding ?? ''],
                      ['Realized vol 20d', fmt2(sig?.realized_vol_20d), '', sig?.realized_vol_20d > 8 ? 'ELEVATED' : ''],
                      ['Realized vol 5d', fmt2(sig?.realized_vol_5d), '', ''],
                      ['Implied vol 30d', sig?.implied_vol_30d != null ? fmt2(sig?.implied_vol_30d) : '—', '', sig?.implied_vol_30d > sig?.realized_vol_20d ? 'IV > RV' : 'IV < RV'],
                      ['Signal composite', fmt2(call?.signal_composite), composite >= 0 ? '↑' : '↓', ''],
                      ['Spot', sig?.spot?.toFixed(pair.label === 'USDJPY' ? 2 : 4) ?? '—', '', ''],
                    ].map(([label, value, dir, note], i) => (
                      <tr key={label} style={{ borderBottom: '1px solid #0f0f0f', background: i % 2 === 0 ? '#0a0a0a' : '#0c0c0c' }}>
                        <td style={{ padding: '11px 18px', fontSize: 11, color: '#aaa' }}>{label}</td>
                        <td style={{ padding: '11px 18px', fontSize: 13, color: '#ffffff', textAlign: 'left', fontWeight: 700 }}>{value}</td>
                        <td style={{ padding: '11px 18px', fontSize: 13, color: dir === '↑' ? '#4ade80' : dir === '↓' ? '#f87171' : '#555', fontWeight: 700 }}>{dir}</td>
                        <td style={{ padding: '11px 18px', fontSize: 9, color: '#444', letterSpacing: '0.06em' }}>{note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {call?.primary_driver && (
                  <div style={{ padding: '14px 18px', borderTop: '1px solid #141414', background: '#0c0c0c' }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.1em', marginRight: 12 }}>PRIMARY DRIVER</span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#bbb' }}>{call.primary_driver}</span>
                  </div>
                )}
              </div>
            )}

            {/* HISTORY tab */}
            {activeTab === 'history' && (
              <div style={{ border: '1px solid #1a1a1a', borderTop: 'none' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'JetBrains Mono, monospace' }}>
                  <thead>
                    <tr style={{ background: '#0c0c0c', borderBottom: '1px solid #1a1a1a' }}>
                      {['DATE', 'REGIME', 'CONF', 'VALIDATION'].map(h => (
                        <th key={h} style={{ padding: '9px 18px', textAlign: 'left', fontSize: 9, color: '#777', letterSpacing: '0.12em', fontWeight: 600 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h, i) => {
                      const vRow = MOCK_VALIDATION.find(r => r.date === h.date && r.pair === pair.display);
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid #0f0f0f', background: i % 2 === 0 ? '#0a0a0a' : '#0c0c0c' }}>
                          <td style={{ padding: '11px 18px', fontSize: 11, color: '#999' }}>{h.date}</td>
                          <td style={{ padding: '11px 18px', fontSize: 11, color: '#f0f0f0', fontWeight: 700 }}>{h.regime}</td>
                          <td style={{ padding: '11px 18px', fontSize: 12, color: pair.pairColor, fontWeight: 700 }}>{Math.round(h.confidence * 100)}%</td>
                          <td style={{ padding: '11px 18px', fontSize: 11, fontWeight: 700, color: vRow ? (vRow.outcome === 'correct' ? '#4ade80' : '#f87171') : '#333' }}>
                            {vRow ? `${vRow.outcome === 'correct' ? '✓' : '✗'} ${vRow.return_pct >= 0 ? '+' : ''}${vRow.return_pct.toFixed(2)}%` : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* CHARTS tab */}
            {activeTab === 'charts' && (
              <div style={{ border: '1px solid #1a1a1a', borderTop: 'none', padding: '20px 18px' }}>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em', marginBottom: 14 }}>CONFIDENCE TREND (7D)</p>
                <svg width="100%" height="80" viewBox="0 0 600 80" preserveAspectRatio="none" style={{ display: 'block', marginBottom: 6 }}>
                  <defs>
                    <linearGradient id={`g-${pair.urlSlug}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={pair.pairColor} stopOpacity="0.25" />
                      <stop offset="100%" stopColor={pair.pairColor} stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  {(() => {
                    const vals = history.map(h => h.confidence);
                    const mn = Math.min(...vals) - 0.05, mx = Math.max(...vals) + 0.05;
                    const n = vals.length;
                    const pts = vals.map((v, i) => [i / (n - 1) * 600, 72 - (v - mn) / (mx - mn) * 64]);
                    const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
                    const area = `${line} L600,80 L0,80 Z`;
                    return (
                      <>
                        <path d={area} fill={`url(#g-${pair.urlSlug})`} />
                        <path d={line} fill="none" stroke={pair.pairColor} strokeWidth="1.5" />
                        {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="3" fill={pair.pairColor} stroke="#080808" strokeWidth="1.5" />)}
                      </>
                    );
                  })()}
                </svg>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
                  {history.map((h, i) => (
                    <span key={i} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#333' }}>{h.date.slice(5)}</span>
                  ))}
                </div>
                <div style={{ border: '1px solid #1a1a1a', padding: '14px 16px', background: '#0c0c0c' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#666', letterSpacing: '0.1em', lineHeight: 1.8 }}>
                    TRADINGVIEW LIGHTWEIGHT CHARTS V5 — PRICE SERIES · REGIME OVERLAYS · SIGNAL BANDS — IN PRODUCTION
                  </p>
                </div>
              </div>
            )}

            {/* ATTRIBUTION tab */}
            {activeTab === 'attribution' && (
              <div style={{ border: '1px solid #1a1a1a', borderTop: 'none' }}>
                <div style={{ padding: '14px 18px', borderBottom: '1px solid #141414', background: '#0c0c0c' }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em' }}>FACTOR ATTRIBUTION — TODAY'S CALL</span>
                </div>
                <div style={{ padding: '20px 18px' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555', letterSpacing: '0.1em', marginBottom: 16 }}>SIGNAL CONTRIBUTION TO COMPOSITE</p>
                  {[
                    { family: 'RATE', label: 'Rate Differential 2Y', weight: 0.40, color: BRAND.eurusd, contrib: -(MOCK_SIGNALS[pair.label]?.rate_diff_2y ?? 0) * 0.4 / 5 * 2 },
                    { family: 'COT', label: 'COT Positioning', weight: 0.30, color: BRAND.usdjpy, contrib: ((MOCK_SIGNALS[pair.label]?.cot_percentile ?? 50) - 50) / 50 * 0.3 * 2 },
                    { family: 'VOL', label: 'Realized Volatility', weight: 0.20, color: BRAND.usdinr, contrib: (MOCK_SIGNALS[pair.label]?.realized_vol_20d ?? 0) > 8 ? -0.08 : 0.04 },
                    { family: 'OI', label: 'OI / Risk Reversals', weight: 0.10, color: '#888', contrib: 0.02 },
                  ].map((f) => {
                    const pctBar = Math.min(100, Math.abs(f.contrib) / 2 * 100);
                    const isPos = f.contrib >= 0;
                    return (
                      <div key={f.family} style={{ marginBottom: 22 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: f.color, fontWeight: 700, letterSpacing: '0.08em' }}>{f.family}</span>
                            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888' }}>{f.label}</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'baseline', gap: 14 }}>
                            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444' }}>weight {(f.weight * 100).toFixed(0)}%</span>
                            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: isPos ? '#4ade80' : '#f87171', fontWeight: 700 }}>{isPos ? '+' : ''}{f.contrib.toFixed(3)}</span>
                          </div>
                        </div>
                        <div style={{ position: 'relative', height: 8, background: '#141414' }}>
                          <div style={{ position: 'absolute', left: '50%', top: 0, width: 1, height: '100%', background: '#2a2a2a' }} />
                          <div style={{ position: 'absolute', left: isPos ? '50%' : `${50 - pctBar / 2}%`, width: `${pctBar / 2}%`, height: '100%', background: isPos ? f.color : f.color + '88' }} />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#2a2a2a' }}>BEARISH</span>
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#2a2a2a' }}>BULLISH</span>
                        </div>
                      </div>
                    );
                  })}
                  <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: 16, marginTop: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>COMPOSITE RESULT</span>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 700, letterSpacing: '-0.03em', color: composite >= 0 ? '#4ade80' : '#f87171' }}>
                        {composite >= 0 ? '+' : ''}{fmt2(call?.signal_composite)}
                      </span>
                    </div>
                    <div style={{ marginTop: 10, background: '#141414', height: 4, position: 'relative' }}>
                      <div style={{ position: 'absolute', left: '50%', top: -2, width: 2, height: 8, background: '#333' }} />
                      <div style={{ position: 'absolute', left: `${Math.min(50, compPct)}%`, width: `${Math.abs(compPct - 50)}%`, height: '100%', background: composite >= 0 ? '#4ade80' : '#f87171' }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#2a2a2a' }}>BEAR -2.0</span>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#2a2a2a' }}>BULL +2.0</span>
                    </div>
                  </div>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#2a2a2a', marginTop: 20, lineHeight: 1.8 }}>
                    WEIGHTS: RATE 40% · COT 30% · VOL 20% · OI/RR 10% · READ FROM config.py IN PRODUCTION
                  </p>
                </div>
              </div>
            )}

            {/* CALENDAR tab */}
            {activeTab === 'calendar' && (
              <PairCalendarTab pair={pair} navigate={navigate} />
            )}

            {/* AI tab */}
            {activeTab === 'ai' && (
              <div style={{ border: '1px solid #1a1a1a', borderTop: 'none' }}>
                <div style={{ padding: '14px 18px', borderBottom: '1px solid #141414', background: '#0c0c0c', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: BRAND.accent, letterSpacing: '0.12em' }}>✦ AI ANALYTICS · {pair.display}</span>
                  </div>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>Powered by Claude · claude-haiku-4-5</span>
                </div>
                <div style={{ padding: '20px 18px' }}>
                  <AiAnalysisPanel pair={pair} call={call} sig={sig} />
                </div>
              </div>
            )}
          </div>

          {/* ─ Right sidebar ─ */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, position: 'relative' }}>

            {/* Collapse toggle */}
            <button onClick={() => setSidebarCollapsed(v => !v)}
              style={{ position: 'absolute', top: 8, left: sidebarCollapsed ? 8 : -14, zIndex: 10, width: 28, height: 28, background: '#1a1a1a', border: '1px solid #2a2a2a', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'left 0.25s ease' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#555', transform: sidebarCollapsed ? 'rotate(180deg)' : 'none', display: 'inline-block', transition: 'transform 0.25s' }}>›</span>
            </button>

            {/* Collapsed state: vertical icon strip */}
            {sidebarCollapsed && (
              <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 0 16px', gap: 18 }}>
                {[
                  { label: 'OTHER DESKS', icon: '⊞', color: '#444' },
                  { label: 'VALIDATION', icon: '✓', color: '#444' },
                  { label: 'PIPELINE', icon: '●', color: '#4ade80' },
                  { label: 'EVENTS', icon: '⚑', color: '#444' },
                  { label: 'AI', icon: '✦', color: BRAND.accent },
                ].map(({ label, icon, color }) => (
                  <button key={label} onClick={() => setSidebarCollapsed(false)}
                    title={label}
                    style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color, background: 'none', cursor: 'pointer', padding: 0 }}>
                    {icon}
                  </button>
                ))}
              </div>
            )}

            {/* Expanded sidebar */}
            {!sidebarCollapsed && (
              <>
                {/* Other Desks */}
                <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', padding: '12px 14px' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em', marginBottom: 10 }}>OTHER DESKS</p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {PAIRS.filter(p => p.label !== pair.label).map(p => (
                      <div key={p.label} onClick={() => navigate(`/terminal/fx-regime/${p.urlSlug}`)} style={{ cursor: 'pointer' }}>
                        <RegimeCard call={MOCK_REGIME_CALLS[p.label]} signals={MOCK_SIGNALS[p.label]} pairDisplay={p.display} />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Validation */}
                <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', padding: '14px' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em', marginBottom: 12 }}>RECENT VALIDATION</p>
                  {MOCK_VALIDATION.filter(r => r.pair === pair.display).slice(0, 3).map((r, i) => (
                    <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 8, alignItems: 'center', padding: '8px 0', borderBottom: i < 2 ? '1px solid #111' : 'none' }}>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#999' }}>{r.date}</span>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: r.outcome === 'correct' ? '#4ade80' : '#f87171', fontWeight: 700 }}>
                        {r.outcome === 'correct' ? '✓' : '✗'}
                      </span>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: r.return_pct >= 0 ? '#4ade80' : '#f87171' }}>
                        {r.return_pct >= 0 ? '+' : ''}{r.return_pct.toFixed(2)}%
                      </span>
                    </div>
                  ))}
                  <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #141414', display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444' }}>7D ACCURACY</span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: '#4ade80' }}>77.8%</span>
                  </div>
                </div>

                {/* Pipeline status */}
                <div style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', padding: '12px 14px' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em', marginBottom: 8 }}>PIPELINE STATUS</p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ade80' }} />
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#aaa' }}>LIVE · {TODAY} 07:12 UTC</span>
                  </div>
                  {[['SIGNALS', 'OK'], ['REGIME CALLS', 'OK'], ['VALIDATION', 'OK'], ['BRIEF', 'OK']].map(([label, status]) => (
                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #0f0f0f' }}>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888', letterSpacing: '0.06em' }}>{label}</span>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#4ade80', fontWeight: 700 }}>{status}</span>
                    </div>
                  ))}
                </div>

                {/* Pair Calendar Widget */}
                <PairCalendarWidget pair={pair} />

                {/* AI Analytics (sidebar compact) */}
                <AiAnalysisPanel pair={pair} call={call} sig={sig} />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { TerminalIndexPage, TerminalStrategyPage, TerminalPairDeskPage });
