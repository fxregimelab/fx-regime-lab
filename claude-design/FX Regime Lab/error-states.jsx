
// ─── ErrorBoundaryCard ────────────────────────────────────────────────────────
function ErrorBoundaryCard({ message = 'Failed to load data.', onRetry, tone = 'shell' }) {
  const isD = tone === 'terminal';
  return (
    <div style={{
      background: isD ? '#0c0c0c' : '#fff',
      border: `1px solid ${isD ? '#1e1e1e' : '#e5e5e5'}`,
      borderLeft: `3px solid ${isD ? '#f87171' : '#dc2626'}`,
      padding: '16px 20px',
      display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16,
    }}>
      <div>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: isD ? '#f87171' : '#dc2626', letterSpacing: '0.12em', marginBottom: 6 }}>ERROR</p>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: isD ? '#888' : '#525252', lineHeight: 1.6 }}>{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry}
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: isD ? '#f87171' : '#dc2626', border: `1px solid ${isD ? '#f8717140' : '#dc262640'}`, background: isD ? '#f8717110' : '#fff5f5', padding: '6px 14px', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0, letterSpacing: '0.06em' }}>
          ↺ Retry
        </button>
      )}
    </div>
  );
}

// ─── EmptyState ───────────────────────────────────────────────────────────────
function EmptyState({ title = 'No data', subtitle = 'Nothing to show here yet.', tone = 'shell' }) {
  const isD = tone === 'terminal';
  return (
    <div style={{ padding: '48px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, background: isD ? '#0c0c0c' : '#fafafa', border: `1px solid ${isD ? '#1a1a1a' : '#e5e5e5'}` }}>
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <rect x="4" y="4" width="24" height="24" stroke={isD ? '#2a2a2a' : '#d0d0d0'} strokeWidth="1.5" />
        <line x1="10" y1="16" x2="22" y2="16" stroke={isD ? '#2a2a2a' : '#d0d0d0'} strokeWidth="1.5" />
      </svg>
      <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 15, color: isD ? '#444' : '#0a0a0a', margin: 0 }}>{title}</p>
      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: isD ? '#333' : '#737373', margin: 0, textAlign: 'center', maxWidth: 280 }}>{subtitle}</p>
    </div>
  );
}

// ─── PipelineOfflineCard ──────────────────────────────────────────────────────
function PipelineOfflineCard() {
  const [countdown, setCountdown] = React.useState(47);
  React.useEffect(() => {
    const t = setInterval(() => setCountdown(c => c > 0 ? c - 1 : 60), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{ background: '#0c0c0c', border: '1px solid #1e1e1e', padding: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#f87171', display: 'inline-block' }} />
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#f87171', fontWeight: 700, letterSpacing: '0.08em' }}>PIPELINE OFFLINE</span>
      </div>
      {[['SIGNALS', 'FAILED'], ['REGIME CALLS', 'STALE'], ['VALIDATION', 'STALE'], ['BRIEF', 'MISSING']].map(([label, status]) => (
        <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #0f0f0f' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888', letterSpacing: '0.06em' }}>{label}</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: status === 'FAILED' ? '#f87171' : '#fbbf24', fontWeight: 700 }}>{status}</span>
        </div>
      ))}
      <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #141414', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>Last run: {TODAY} 07:12 UTC</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555' }}>Retry in {countdown}s</span>
      </div>
    </div>
  );
}

// ─── NoCalendarEventsState ────────────────────────────────────────────────────
function NoCalendarEventsState({ pair = null }) {
  return (
    <div style={{ padding: '40px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, border: '1px solid #e5e5e5', background: '#fafafa' }}>
      <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
        <rect x="4" y="8" width="28" height="24" stroke="#d0d0d0" strokeWidth="1.5" />
        <line x1="4" y1="14" x2="32" y2="14" stroke="#d0d0d0" strokeWidth="1.5" />
        <line x1="12" y1="4" x2="12" y2="10" stroke="#d0d0d0" strokeWidth="1.5" />
        <line x1="24" y1="4" x2="24" y2="10" stroke="#d0d0d0" strokeWidth="1.5" />
        <line x1="12" y1="22" x2="24" y2="22" stroke="#d0d0d0" strokeWidth="1.5" />
      </svg>
      <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 14, color: '#0a0a0a', margin: 0 }}>No events scheduled</p>
      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', margin: 0, textAlign: 'center', maxWidth: 260 }}>
        {pair ? `No upcoming macro events found for ${pair}.` : 'No macro events match the current filter.'}
      </p>
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb', marginTop: 4 }}>Try selecting ALL pairs or check back later.</p>
    </div>
  );
}

// ─── NoValidationDataState ────────────────────────────────────────────────────
function NoValidationDataState() {
  return (
    <div style={{ padding: '32px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, border: '1px solid #e5e5e5' }}>
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <rect x="4" y="4" width="24" height="24" stroke="#d0d0d0" strokeWidth="1.5" />
        {[8,14,20].map(y => <line key={y} x1="8" y1={y} x2="24" y2={y} stroke="#ebebeb" strokeWidth="1" />)}
      </svg>
      <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 14, color: '#0a0a0a', margin: 0 }}>No validation history yet</p>
      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', margin: 0, textAlign: 'center', maxWidth: 280 }}>
        Regime calls are validated the following trading day. Check back after market close.
      </p>
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb', marginTop: 4 }}>Pipeline runs daily at 07:00 UTC</p>
    </div>
  );
}

// ─── AiErrorState ─────────────────────────────────────────────────────────────
function AiErrorState({ onRetry, pairColor = BRAND.accent }) {
  return (
    <div style={{ background: '#0c0c0c', border: '1px solid #1e1e1e', borderTop: `2px solid #f87171`, padding: '20px 18px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, textAlign: 'center' }}>
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <polygon points="14,4 26,24 2,24" stroke="#f87171" strokeWidth="1.5" fill="none" />
        <line x1="14" y1="11" x2="14" y2="17" stroke="#f87171" strokeWidth="1.5" />
        <circle cx="14" cy="20" r="1" fill="#f87171" />
      </svg>
      <div>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#f87171', letterSpacing: '0.1em', marginBottom: 6, fontWeight: 700 }}>GENERATION FAILED</p>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#444', lineHeight: 1.6 }}>AI analysis could not be generated. Check your connection or try again.</p>
      </div>
      {onRetry && (
        <button onClick={onRetry}
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: pairColor, border: `1px solid ${pairColor}40`, background: `${pairColor}10`, padding: '8px 20px', cursor: 'pointer', letterSpacing: '0.06em', fontWeight: 700 }}>
          ↺ RETRY GENERATION
        </button>
      )}
    </div>
  );
}

// ─── AiRateLimitState ─────────────────────────────────────────────────────────
function AiRateLimitState() {
  const now = new Date();
  const midnight = new Date(now);
  midnight.setUTCHours(24, 0, 0, 0);
  const hoursLeft = Math.ceil((midnight - now) / 3600000);

  return (
    <div style={{ background: '#0c0c0c', border: '1px solid #1e1e1e', borderTop: '2px solid #fbbf24', padding: '20px 18px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, textAlign: 'center' }}>
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <circle cx="14" cy="14" r="10" stroke="#fbbf24" strokeWidth="1.5" />
        <line x1="14" y1="8" x2="14" y2="14" stroke="#fbbf24" strokeWidth="1.5" />
        <line x1="14" y1="14" x2="18" y2="17" stroke="#fbbf24" strokeWidth="1.5" />
      </svg>
      <div>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#fbbf24', letterSpacing: '0.1em', marginBottom: 6, fontWeight: 700 }}>DAILY AI BUDGET REACHED</p>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#444', lineHeight: 1.6 }}>AI generation resets at midnight UTC. Cached briefs remain available.</p>
      </div>
      <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555', letterSpacing: '0.08em' }}>RESETS IN</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, color: '#fbbf24', fontWeight: 700 }}>{hoursLeft}h</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>at 00:00 UTC</span>
      </div>
    </div>
  );
}

// ─── ChartLoadErrorState ──────────────────────────────────────────────────────
function ChartLoadErrorState({ onRetry }) {
  return (
    <div style={{ border: '1px solid #1a1a1a', borderTop: 'none', padding: '40px 20px', background: '#0a0a0a', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
      <div style={{ width: '100%', height: 80, border: '1px dashed #1e1e1e', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8 }}>
        <svg width="200" height="60" viewBox="0 0 200 60" preserveAspectRatio="none">
          {[0,1,2,3].map(i => (
            <line key={i} x1={i * 50 + 10} y1="10" x2={i * 50 + 40} y2="50" stroke="#1e1e1e" strokeWidth="1" strokeDasharray="4,3" />
          ))}
        </svg>
      </div>
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#f87171', letterSpacing: '0.12em', marginBottom: 6 }}>CHART LOAD ERROR</p>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#444', lineHeight: 1.6 }}>Could not load chart data. TradingView integration pending.</p>
      </div>
      {onRetry && (
        <button onClick={onRetry}
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', border: '1px solid #1e1e1e', background: 'none', padding: '7px 16px', cursor: 'pointer', letterSpacing: '0.06em' }}>
          ↺ Retry
        </button>
      )}
    </div>
  );
}

// ─── ErrorStatesDemo ──────────────────────────────────────────────────────────
function ErrorStatesDemo({ navigate }) {
  const [retryCount, setRetryCount] = React.useState(0);
  const sections = [
    { label: 'ErrorBoundaryCard — Shell', content: <ErrorBoundaryCard message="Failed to load regime calls. Check your connection." onRetry={() => setRetryCount(c => c + 1)} tone="shell" /> },
    { label: 'ErrorBoundaryCard — Terminal', content: <div style={{ background: '#080808', padding: 16 }}><ErrorBoundaryCard message="Signal pipeline returned an error. Last known data shown." onRetry={() => setRetryCount(c => c + 1)} tone="terminal" /></div> },
    { label: 'EmptyState — Shell', content: <EmptyState title="No validation data" subtitle="Regime calls are logged daily. Come back after market open." tone="shell" /> },
    { label: 'EmptyState — Terminal', content: <div style={{ background: '#080808', padding: 0 }}><EmptyState title="No signals loaded" subtitle="Pipeline has not run yet for this session." tone="terminal" /></div> },
    { label: 'PipelineOfflineCard', content: <div style={{ background: '#080808', padding: 16, maxWidth: 300 }}><PipelineOfflineCard /></div> },
    { label: 'NoCalendarEventsState', content: <NoCalendarEventsState pair="USD/INR" /> },
    { label: 'NoValidationDataState', content: <NoValidationDataState /> },
    { label: 'AiErrorState', content: <div style={{ background: '#080808', padding: 16 }}><AiErrorState onRetry={() => setRetryCount(c => c + 1)} pairColor={BRAND.eurusd} /></div> },
    { label: 'AiRateLimitState', content: <div style={{ background: '#080808', padding: 16 }}><AiRateLimitState /></div> },
    { label: 'ChartLoadErrorState', content: <div style={{ background: '#080808' }}><ChartLoadErrorState onRetry={() => setRetryCount(c => c + 1)} /></div> },
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#fafafa' }}>
      <div style={{ background: '#0a0a0a', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#555', letterSpacing: '0.1em' }}>ERROR STATES DEMO</span>
          {retryCount > 0 && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#4ade80' }}>Retry pressed {retryCount}×</span>}
        </div>
        {navigate && (
          <button onClick={() => navigate('/')} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#555', border: '1px solid #1e1e1e', padding: '6px 12px', background: 'none', cursor: 'pointer' }}>← Shell</button>
        )}
      </div>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 24px', display: 'flex', flexDirection: 'column', gap: 40 }}>
        {sections.map((s, i) => (
          <div key={i}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.12em', marginBottom: 12 }}>{(i + 1).toString().padStart(2, '0')} — {s.label.toUpperCase()}</p>
            {s.content}
          </div>
        ))}
        <div style={{ paddingTop: 20, borderTop: '1px solid #e5e5e5' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#ccc' }}>ERROR STATES REVIEW · {sections.length} VARIANTS · FX REGIME LAB</p>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  ErrorBoundaryCard, EmptyState, PipelineOfflineCard,
  NoCalendarEventsState, NoValidationDataState,
  AiErrorState, AiRateLimitState, ChartLoadErrorState,
  ErrorStatesDemo,
});
