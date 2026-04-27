
// ─── Calendar Page — AI-enhanced ─────────────────────────────────────────────
function CalendarPage({ navigate }) {
  const [filterPair, setFilterPair] = React.useState('ALL');
  const [expandedEvent, setExpandedEvent] = React.useState(null);
  const [aiBriefs, setAiBriefs] = React.useState({});
  const [aiLoading, setAiLoading] = React.useState({});
  const today = new Date(TODAY);

  const impactColor = (impact) => impact === 'HIGH' ? '#D94030' : impact === 'MEDIUM' ? '#F5923A' : '#888';
  const categoryColor = { US: '#4BA3E3', EU: '#888', JP: '#F5923A', IN: '#D94030', UK: '#aaa' };

  const filtered = filterPair === 'ALL'
    ? MOCK_CALENDAR
    : MOCK_CALENDAR.filter(e => e.pairs.includes(filterPair));

  const grouped = filtered.reduce((acc, e) => {
    acc[e.date] = acc[e.date] || [];
    acc[e.date].push(e);
    return acc;
  }, {});

  const daysUntil = (dateStr) => Math.ceil((new Date(dateStr) - today) / 86400000);

  const eventKey = (e) => `${e.date}-${e.event}`;

  const generateBrief = async (e) => {
    const key = eventKey(e);
    if (aiBriefs[key] || aiLoading[key]) return;
    setAiLoading(prev => ({ ...prev, [key]: true }));

    const pairNames = e.pairs.map(lbl => PAIRS.find(p => p.label === lbl)?.display).filter(Boolean).join(', ');

    // Get current regime context for relevant pairs
    const regimeContext = e.pairs.map(lbl => {
      const pm = PAIRS.find(p => p.label === lbl);
      const rc = MOCK_REGIME_CALLS[lbl];
      return pm && rc ? `${pm.display}: ${rc.regime} (${Math.round(rc.confidence * 100)}% conf)` : null;
    }).filter(Boolean).join('; ');

    try {
      const prompt = `You are a professional FX macro analyst. Write a structured event brief for traders.

EVENT: ${e.event}
DATE: ${e.date} (${daysUntil(e.date) === 0 ? 'TODAY' : daysUntil(e.date) === 1 ? 'TOMORROW' : daysUntil(e.date) + ' days away'})
IMPACT: ${e.impact}
CATEGORY: ${e.category}
RELEVANT FX PAIRS: ${pairNames || 'USD pairs broadly'}
CURRENT REGIME CONTEXT: ${regimeContext || 'N/A'}

Write your response using EXACTLY these section headers:

OVERVIEW
[2 sentences: what this event is and what it measures]

EXPECTATIONS
[Current market consensus — be specific with forecast numbers, prior print, and range of estimates where relevant]

WHY IT MATTERS
[2-3 sentences on the FX transmission mechanism — how this data moves the pairs listed, and why now]

SCENARIOS
BEAT (X%): [Data beats consensus — impact on ${pairNames || 'USD'} with likely move description]
IN LINE (X%): [Data matches consensus — muted reaction, what it means for regime]
MISS (X%): [Data misses consensus — impact on ${pairNames || 'USD'} with likely move description]

REGIME IMPLICATIONS
[1-2 sentences on how this event could shift or confirm the current FX regime for the relevant pairs]

Probabilities must sum to 100%. Be specific and analytical. No marketing language.`;

      const text = await window.claude.complete(prompt);
      setAiBriefs(prev => ({ ...prev, [key]: text }));
    } catch {
      setAiBriefs(prev => ({ ...prev, [key]: '__ERROR__' }));
    }
    setAiLoading(prev => ({ ...prev, [key]: false }));
  };

  const handleExpand = (e) => {
    const key = eventKey(e);
    const isOpen = expandedEvent === key;
    const next = isOpen ? null : key;
    setExpandedEvent(next);
    if (!isOpen) generateBrief(e);
  };

  const parseSection = (text, header) => {
    const re = new RegExp(`${header}\\n([\\s\\S]*?)(?=\\n[A-Z][A-Z ]+\\n|$)`);
    const m = text.match(re);
    return m ? m[1].trim() : null;
  };

  const parseScenarios = (text) => {
    const scenarios = [];
    const lines = text.split('\n');
    lines.forEach(line => {
      const m = line.match(/^(BEAT|IN LINE|MISS)\s*\((\d+)%\):\s*(.+)/i);
      if (m) scenarios.push({ type: m[1].toUpperCase(), prob: parseInt(m[2]), desc: m[3].trim() });
    });
    return scenarios;
  };

  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px' }}>

      {/* Header */}
      <div style={{ marginBottom: 40, paddingBottom: 24, borderBottom: '1px solid #e5e5e5' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 10 }}>MACRO CALENDAR</p>
            <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 32, color: '#0a0a0a', letterSpacing: '-0.03em', margin: '0 0 8px' }}>Event Calendar</h1>
            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#737373' }}>
              High-impact macro events relevant to G10 FX regime calls. Click any event for AI brief — expectations, scenarios, and regime implications.
            </p>
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 32 }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#aaa' }}>Viewing from {TODAY}</p>
            <div style={{ display: 'flex', gap: 14, marginTop: 8, justifyContent: 'flex-end', alignItems: 'center' }}>
              {[['HIGH', '#D94030'], ['MEDIUM', '#F5923A']].map(([label, color]) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ width: 8, height: 8, background: color, display: 'inline-block', flexShrink: 0 }} />
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888' }}>{label}</span>
                </div>
              ))}
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#0a0a0a', background: '#f0f0f0', padding: '2px 7px' }}>✦ AI</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888' }}>brief on click</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* FOMC countdown banner */}
      {(() => {
        const fomc = MOCK_CALENDAR.find(e => e.event.includes('FOMC Rate'));
        if (!fomc) return null;
        const days = daysUntil(fomc.date);
        return (
          <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', padding: '16px 20px', marginBottom: 32, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ background: '#D94030', width: 4, height: 40, flexShrink: 0 }} />
              <div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444', letterSpacing: '0.12em', marginBottom: 4 }}>HIGH IMPACT · NEXT MAJOR EVENT</p>
                <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 15, color: '#f0f0f0' }}>{fomc.event}</p>
                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  {fomc.pairs.map(lbl => {
                    const pm = PAIRS.find(p => p.label === lbl);
                    return pm ? <span key={lbl} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: pm.pairColor }}>{pm.display}</span> : null;
                  })}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
              <div style={{ textAlign: 'right' }}>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 28, fontWeight: 700, color: '#D94030', letterSpacing: '-0.03em', lineHeight: 1 }}>{days}d</p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444', marginTop: 3 }}>{fomc.date}</p>
              </div>
              <button onClick={() => handleExpand(fomc)}
                style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#D94030', border: '1px solid #D9403040', background: '#D9403010', padding: '8px 14px', cursor: 'pointer', letterSpacing: '0.06em' }}>
                ✦ AI BRIEF
              </button>
            </div>
          </div>
        );
      })()}

      {/* Pair filter */}
      <div style={{ display: 'flex', gap: 1, marginBottom: 28, borderBottom: '1px solid #e5e5e5' }}>
        {['ALL', ...PAIRS.map(p => p.display)].map(label => {
          const pairMeta = PAIRS.find(p => p.display === label);
          const active = filterPair === (label === 'ALL' ? 'ALL' : pairMeta?.label ?? label);
          return (
            <button key={label}
              onClick={() => setFilterPair(label === 'ALL' ? 'ALL' : pairMeta?.label ?? label)}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '9px 16px', color: active ? '#0a0a0a' : '#999', borderBottom: active ? `2px solid ${pairMeta?.pairColor ?? '#0a0a0a'}` : '2px solid transparent', marginBottom: -1, fontWeight: active ? 700 : 400, letterSpacing: '0.06em' }}>
              {label}
            </button>
          );
        })}
        <span style={{ marginLeft: 'auto', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb', alignSelf: 'center' }}>{filtered.length} events</span>
      </div>

      {/* Event list grouped by date */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([date, events]) => {
          const days = daysUntil(date);
          const dateObj = new Date(date + 'T00:00:00Z');
          const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' });
          const dayNum = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
          const isToday = days === 0;
          const isTomorrow = days === 1;

          return (
            <div key={date} style={{ border: '1px solid #e5e5e5', borderBottom: 'none' }}>
              {events.map((e, ei) => {
                const key = eventKey(e);
                const isOpen = expandedEvent === key;
                const brief = aiBriefs[key];
                const loading = aiLoading[key];
                const impactPairs = e.pairs.map(lbl => PAIRS.find(p => p.label === lbl)).filter(Boolean);
                const hasHighImpact = e.impact === 'HIGH';

                const overview = brief && brief !== '__ERROR__' ? parseSection(brief, 'OVERVIEW') : null;
                const expectations = brief && brief !== '__ERROR__' ? parseSection(brief, 'EXPECTATIONS') : null;
                const whyMatters = brief && brief !== '__ERROR__' ? parseSection(brief, 'WHY IT MATTERS') : null;
                const scenariosRaw = brief && brief !== '__ERROR__' ? parseSection(brief, 'SCENARIOS') : null;
                const regimeImplications = brief && brief !== '__ERROR__' ? parseSection(brief, 'REGIME IMPLICATIONS') : null;
                const scenarios = scenariosRaw ? parseScenarios(scenariosRaw) : [];

                return (
                  <div key={key} style={{ borderBottom: '1px solid #f0f0f0' }}>

                    {/* Event row */}
                    <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr', gap: 0 }}>
                      {/* Date column — only show for first event of date */}
                      {ei === 0 ? (
                        <div style={{ padding: '16px', borderRight: '1px solid #f0f0f0', background: isToday ? '#fff8f0' : isTomorrow ? '#fafafa' : '#fafafa', display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', rowSpan: events.length }}>
                          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.08em', marginBottom: 2 }}>{dayName.toUpperCase()}</p>
                          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 700, color: isToday ? BRAND.accent : '#0a0a0a' }}>{dayNum}</p>
                          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, marginTop: 4, fontWeight: days <= 2 ? 700 : 400, color: days === 0 ? '#D94030' : days === 1 ? '#F5923A' : '#bbb' }}>
                            {days === 0 ? 'TODAY' : days === 1 ? 'TOMORROW' : `${days}d`}
                          </p>
                          {events.length > 1 && (
                            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#ccc', marginTop: 8 }}>{events.length} events</p>
                          )}
                        </div>
                      ) : (
                        <div style={{ borderRight: '1px solid #f0f0f0', background: '#fafafa' }} />
                      )}

                      {/* Event content */}
                      <div>
                        {/* Clickable event header */}
                        <button onClick={() => handleExpand(e)}
                          style={{ width: '100%', display: 'grid', gridTemplateColumns: '4px 1fr auto', gap: 16, alignItems: 'center', padding: '14px 20px', background: isOpen ? '#fafafa' : 'white', cursor: 'pointer', textAlign: 'left', transition: 'background 0.1s' }}
                          onMouseEnter={ev => { if (!isOpen) ev.currentTarget.style.background = '#fafafa'; }}
                          onMouseLeave={ev => { if (!isOpen) ev.currentTarget.style.background = 'white'; }}>

                          {/* Impact indicator */}
                          <div style={{ background: impactColor(e.impact), alignSelf: 'stretch', minHeight: 36, width: 4 }} />

                          {/* Event info */}
                          <div>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4, flexWrap: 'wrap' }}>
                              <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 14, color: '#0a0a0a' }}>{e.event}</p>
                              {brief && brief !== '__ERROR__' && (
                                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#22c55e', background: '#f0fdf4', padding: '2px 6px', border: '1px solid #d1fae5' }}>✦ AI BRIEF READY</span>
                              )}
                            </div>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: categoryColor[e.category] || '#888', fontWeight: 700, letterSpacing: '0.08em' }}>{e.category}</span>
                              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#ddd' }}>·</span>
                              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: impactColor(e.impact), fontWeight: 700, letterSpacing: '0.06em' }}>{e.impact} IMPACT</span>
                              {impactPairs.map(pm => (
                                <span key={pm.label} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: pm.pairColor, letterSpacing: '0.06em' }}>· {pm.display}</span>
                              ))}
                            </div>
                          </div>

                          {/* Right side: expand icon */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                            {loading && (
                              <div style={{ display: 'flex', gap: 2 }}>
                                {[0,1,2].map(i => <div key={i} style={{ width: 4, height: 4, background: '#0a0a0a', opacity: 0.4, animation: `pulse 1.2s ${i*0.2}s infinite` }} />)}
                              </div>
                            )}
                            {!loading && !brief && (
                              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.06em' }}>✦ AI</span>
                            )}
                            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, color: '#aaa', transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s', display: 'inline-block' }}>›</span>
                          </div>
                        </button>

                        {/* Expanded AI Brief */}
                        {isOpen && (
                          <div style={{ background: '#fafafa', borderTop: '1px solid #ebebeb' }}>

                            {/* Loading state */}
                            {loading && (
                              <div style={{ padding: '24px 20px', display: 'flex', alignItems: 'center', gap: 12 }}>
                                <div style={{ display: 'flex', gap: 4 }}>
                                  {[0,1,2].map(i => (
                                    <div key={i} style={{ width: 6, height: 6, background: hasHighImpact ? '#D94030' : '#F5923A', animation: `pulse 1.2s ${i*0.2}s infinite` }} />
                                  ))}
                                </div>
                                <div>
                                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#777', marginBottom: 2 }}>Generating AI brief for {e.event}…</p>
                                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb' }}>Analyzing expectations, scenarios, and regime implications</p>
                                </div>
                              </div>
                            )}

                            {/* Error state */}
                            {brief === '__ERROR__' && (
                              <div style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#aaa' }}>Could not generate brief.</p>
                                <button onClick={() => { setAiBriefs(prev => { const n = {...prev}; delete n[key]; return n; }); generateBrief(e); }}
                                  style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#555', border: '1px solid #e5e5e5', padding: '6px 12px', background: 'none', cursor: 'pointer' }}>
                                  Retry
                                </button>
                              </div>
                            )}

                            {/* Brief content */}
                            {brief && brief !== '__ERROR__' && !loading && (
                              <div style={{ padding: '20px 24px 24px' }}>

                                {/* Top row: Overview + Expectations */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>

                                  {/* Overview */}
                                  {overview && (
                                    <div style={{ background: '#fff', border: '1px solid #e5e5e5', borderTop: '2px solid #0a0a0a', padding: '16px 18px' }}>
                                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#999', letterSpacing: '0.12em', marginBottom: 8 }}>WHAT IT IS</p>
                                      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#444', lineHeight: 1.7 }}>{overview}</p>
                                    </div>
                                  )}

                                  {/* Expectations */}
                                  {expectations && (
                                    <div style={{ background: '#fff', border: '1px solid #e5e5e5', borderTop: `2px solid ${impactColor(e.impact)}`, padding: '16px 18px' }}>
                                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: impactColor(e.impact), letterSpacing: '0.12em', marginBottom: 8 }}>MARKET EXPECTATIONS</p>
                                      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#111', lineHeight: 1.7, fontWeight: 500 }}>{expectations}</p>
                                    </div>
                                  )}
                                </div>

                                {/* Scenarios */}
                                {scenarios.length > 0 && (
                                  <div style={{ background: '#fff', border: '1px solid #e5e5e5', padding: '16px 18px', marginBottom: 20 }}>
                                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#999', letterSpacing: '0.12em', marginBottom: 14 }}>PROBABILITY SCENARIOS</p>
                                    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${scenarios.length}, 1fr)`, gap: 16 }}>
                                      {scenarios.map((s, si) => {
                                        const scenColor = s.type === 'BEAT' ? '#16a34a' : s.type === 'MISS' ? '#dc2626' : '#737373';
                                        const scenBg = s.type === 'BEAT' ? '#f0fdf4' : s.type === 'MISS' ? '#fff5f5' : '#fafafa';
                                        return (
                                          <div key={si} style={{ background: scenBg, border: `1px solid ${scenColor}20`, padding: '14px 16px' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
                                              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: scenColor, fontWeight: 700, letterSpacing: '0.06em' }}>{s.type}</span>
                                              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, color: scenColor, fontWeight: 700, letterSpacing: '-0.02em' }}>{s.prob}%</span>
                                            </div>
                                            {/* Probability bar */}
                                            <div style={{ background: '#e5e5e5', height: 3, marginBottom: 10 }}>
                                              <div style={{ width: `${s.prob}%`, height: '100%', background: scenColor }} />
                                            </div>
                                            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#555', lineHeight: 1.6 }}>{s.desc}</p>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </div>
                                )}

                                {/* Bottom row: Why it matters + Regime implications */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                                  {whyMatters && (
                                    <div>
                                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.12em', marginBottom: 8 }}>WHY IT MATTERS FOR FX</p>
                                      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', lineHeight: 1.7 }}>{whyMatters}</p>
                                    </div>
                                  )}
                                  {regimeImplications && (
                                    <div style={{ background: '#0a0a0a', padding: '14px 16px' }}>
                                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555', letterSpacing: '0.12em', marginBottom: 8 }}>REGIME IMPLICATIONS</p>
                                      <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                                        {impactPairs.map(pm => {
                                          const rc = MOCK_REGIME_CALLS[pm.label];
                                          return rc ? (
                                            <span key={pm.label} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: pm.pairColor, background: `${pm.pairColor}15`, padding: '2px 7px', fontWeight: 700 }}>
                                              {pm.display}: {rc.regime.split(' ').slice(0,2).join(' ')}
                                            </span>
                                          ) : null;
                                        })}
                                      </div>
                                      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#888', lineHeight: 1.7 }}>{regimeImplications}</p>
                                    </div>
                                  )}
                                </div>

                                {/* Footer */}
                                <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #ebebeb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#ccc' }}>✦ AI-generated brief · Research only · Not investment advice</p>
                                  <button onClick={() => { setAiBriefs(prev => { const n = {...prev}; delete n[key]; return n; }); generateBrief(e); }}
                                    style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', border: '1px solid #e5e5e5', padding: '4px 10px', background: 'none', cursor: 'pointer' }}>
                                    ↺ Regenerate
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })}

        <div style={{ border: '1px solid #e5e5e5', borderTop: 'none', padding: '12px 20px', background: '#fafafa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb' }}>Events sourced from public macro calendar. Times in UTC. Not exhaustive.</p>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#ddd' }}>Click any event for ✦ AI brief</p>
        </div>
      </div>
      <style>{`@keyframes pulse { 0%,100%{opacity:0.2} 50%{opacity:1} }`}</style>
    </div>
  );
}

// ─── Pair Detail Page ─────────────────────────────────────────────────────────
function PairDetailPage({ pairSlug, navigate }) {
  const pair = PAIRS.find(p => p.urlSlug === pairSlug) ?? PAIRS[0];
  const call = MOCK_REGIME_CALLS[pair.label];
  const sig = MOCK_SIGNALS[pair.label];
  const history = MOCK_HISTORY[pair.label] ?? [];
  const pairValidation = MOCK_VALIDATION.filter(r => r.pair === pair.display);
  const accuracy = pairValidation.length ? ((pairValidation.filter(r => r.outcome === 'correct').length / pairValidation.length) * 100).toFixed(0) : '—';
  const pct = call ? Math.round(call.confidence * 100) : null;

  let streak = 1;
  if (history.length > 1) {
    for (let i = 0; i < history.length - 1; i++) {
      if (history[i].regime === history[0].regime) streak++;
      else break;
    }
  }

  // Upcoming events for this pair
  const pairEvents = MOCK_CALENDAR.filter(e => e.pairs.includes(pair.label)).slice(0, 3);

  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px' }}>
      {/* Header */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 32, alignItems: 'start', marginBottom: 40, paddingBottom: 24, borderBottom: '1px solid #e5e5e5' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{ width: 12, height: 12, background: pair.pairColor, flexShrink: 0 }} />
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em' }}>FX REGIME · {pair.label}</p>
          </div>
          <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 40, color: '#0a0a0a', letterSpacing: '-0.035em', margin: '0 0 8px' }}>{pair.display}</h1>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 20, fontWeight: 700, color: '#0a0a0a', letterSpacing: '-0.02em' }}>
            {sig?.spot?.toFixed(pair.label === 'USDJPY' ? 2 : 4) ?? '—'}
            {sig?.day_change_pct != null && (
              <span style={{ fontSize: 13, fontWeight: 600, color: sig.day_change_pct >= 0 ? '#16a34a' : '#dc2626', marginLeft: 10 }}>
                {sig.day_change_pct >= 0 ? '+' : ''}{sig.day_change_pct.toFixed(2)}%
              </span>
            )}
          </p>
        </div>
        <button onClick={() => navigate(`/terminal/fx-regime/${pair.urlSlug}`)}
          style={{ background: '#0a0a0a', color: '#fff', fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 13, padding: '10px 18px', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ade80' }} />
          Open terminal desk
        </button>
      </div>

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Current regime */}
        <div style={{ border: '1px solid #e5e5e5', borderTop: `3px solid ${pair.pairColor}` }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #f0f0f0', background: '#fafafa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>CURRENT REGIME</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: pair.pairColor, background: `${pair.pairColor}15`, padding: '3px 8px', fontWeight: 700 }}>DAY {streak}</span>
          </div>
          <div style={{ padding: '20px' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: '#0a0a0a', letterSpacing: '0.03em', lineHeight: 1.4, marginBottom: 14 }}>{call?.regime ?? '—'}</p>
            <div style={{ marginBottom: 10 }}>
              <ConfidenceBar value={call?.confidence} tone="light" color={pair.pairColor} />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.1em' }}>CONFIDENCE</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#0a0a0a', fontWeight: 700 }}>{pct != null ? `${pct}%` : '—'}</span>
              </div>
            </div>
            {call?.primary_driver && (
              <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', lineHeight: 1.6, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>{call.primary_driver}</p>
            )}
          </div>
        </div>

        {/* Signal snapshot */}
        <div style={{ border: '1px solid #e5e5e5' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #f0f0f0', background: '#fafafa' }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>SIGNAL SNAPSHOT · {TODAY}</span>
          </div>
          <div>
            {[
              ['SPOT', sig?.spot?.toFixed(pair.label === 'USDJPY' ? 2 : 4)],
              ['RATE DIFF 2Y', fmt2(sig?.rate_diff_2y)],
              ['COT PERCENTILE', fmtInt(sig?.cot_percentile)],
              ['REALIZED VOL 20D', fmt2(sig?.realized_vol_20d)],
              ['IMPLIED VOL 30D', sig?.implied_vol_30d != null ? fmt2(sig?.implied_vol_30d) : 'N/A'],
              ['SIGNAL COMPOSITE', fmt2(call?.signal_composite)],
            ].map(([lbl, val], i) => (
              <div key={lbl} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '11px 20px', borderBottom: i < 5 ? '1px solid #f5f5f5' : 'none' }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#aaa', letterSpacing: '0.06em' }}>{lbl}</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 700, color: '#0a0a0a' }}>{val ?? '—'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Upcoming events for pair */}
      {pairEvents.length > 0 && (
        <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #f0f0f0', background: '#fafafa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>UPCOMING EVENTS — {pair.display}</span>
            <button onClick={() => navigate('/calendar')} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb', background: 'none', border: 'none', cursor: 'pointer' }}>Full calendar →</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${pairEvents.length}, 1fr)` }}>
            {pairEvents.map((e, i) => {
              const days = Math.ceil((new Date(e.date) - new Date(TODAY)) / 86400000);
              const impactC = e.impact === 'HIGH' ? '#D94030' : '#F5923A';
              return (
                <div key={i} style={{ padding: '16px 20px', borderRight: i < pairEvents.length - 1 ? '1px solid #f0f0f0' : 'none', borderTop: `2px solid ${impactC}` }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: impactC, fontWeight: 700, letterSpacing: '0.08em', marginBottom: 6 }}>{e.impact} · {days === 0 ? 'TODAY' : days === 1 ? 'TOMORROW' : `${days}d`}</p>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#0a0a0a', fontWeight: 600, marginBottom: 4 }}>{e.event}</p>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#aaa' }}>{e.date}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Regime heatmap */}
      <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #f0f0f0', background: '#fafafa', display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>REGIME HISTORY (30D)</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb' }}>color = regime</span>
        </div>
        <div style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            {MOCK_HEATMAP.dates.map((date, i) => {
              const regime = MOCK_HEATMAP.regimes[pair.label]?.[i] ?? 'UNKNOWN';
              const color = REGIME_HEATMAP_COLORS[regime] ?? '#1a1a1a';
              return (
                <div key={date} title={`${date}: ${regime}`}
                  style={{ width: 20, height: 20, background: color, cursor: 'default', flexShrink: 0 }} />
              );
            })}
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
            {[...new Set(MOCK_HEATMAP.regimes[pair.label])].map(regime => (
              <div key={regime} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 8, height: 8, background: REGIME_HEATMAP_COLORS[regime] ?? '#333', flexShrink: 0, display: 'inline-block' }} />
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888' }}>{regime}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Validation table */}
      <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #f0f0f0', background: '#fafafa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>VALIDATION LOG — {pair.display}</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 700, color: '#16a34a' }}>{accuracy}% accuracy</span>
        </div>
        <ValidationTable rows={pairValidation} tone="light" />
      </div>

      {/* Pair navigation */}
      <div style={{ display: 'flex', gap: 12 }}>
        {PAIRS.filter(p => p.label !== pair.label).map(p => (
          <button key={p.label} onClick={() => navigate(`/pairs/${p.urlSlug}`)}
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: p.pairColor, border: `1px solid ${p.pairColor}40`, padding: '8px 16px', background: 'none', cursor: 'pointer' }}>
            {p.display} →
          </button>
        ))}
        <button onClick={() => navigate('/performance')}
          style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#555', border: '1px solid #e5e5e5', padding: '8px 16px', background: 'none', cursor: 'pointer', marginLeft: 'auto' }}>
          Full performance →
        </button>
      </div>
    </div>
  );
}

// ─── Regime Heatmap ───────────────────────────────────────────────────────────
function RegimeHeatmap({ navigate }) {
  return (
    <div style={{ border: '1px solid #e5e5e5' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e5e5', background: '#fafafa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>REGIME HEATMAP — 30 DAYS</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb' }}>each cell = 1 trading day</span>
      </div>
      {PAIRS.map((p, pi) => (
        <div key={p.label} style={{ display: 'grid', gridTemplateColumns: '80px 1fr', borderBottom: pi < PAIRS.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
          <div style={{ padding: '12px 16px', borderRight: '1px solid #f0f0f0', display: 'flex', alignItems: 'center' }}>
            <button onClick={() => navigate(`/pairs/${p.urlSlug}`)}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: p.pairColor, fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
              {p.display}
            </button>
          </div>
          <div style={{ padding: '12px 16px', display: 'flex', gap: 2, alignItems: 'center', overflowX: 'auto' }}>
            {MOCK_HEATMAP.dates.map((date, i) => {
              const regime = MOCK_HEATMAP.regimes[p.label]?.[i] ?? 'UNKNOWN';
              const color = REGIME_HEATMAP_COLORS[regime] ?? '#1a1a1a';
              return (
                <div key={date} title={`${date}\n${regime}`}
                  style={{ width: 14, height: 28, background: color, flexShrink: 0, cursor: 'default' }} />
              );
            })}
          </div>
        </div>
      ))}
      <div style={{ padding: '10px 20px', background: '#fafafa', borderTop: '1px solid #f0f0f0', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {[
          ['STRONG USD STR', '#1e3a5f'], ['MOD USD STR', '#2d5a8e'], ['NEUTRAL', '#3a3a3a'],
          ['MOD USD WEAK', '#7a3f1f'], ['VOL EXPANDING', '#7a5c00'], ['DEPRECIATION', '#8b2a2a'], ['APPRECIATION', '#1a5a2a'],
        ].map(([label, color]) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 10, height: 10, background: color, display: 'inline-block', flexShrink: 0 }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888' }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { CalendarPage, PairDetailPage, RegimeHeatmap });
