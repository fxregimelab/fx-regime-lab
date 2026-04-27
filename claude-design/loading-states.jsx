
// ─── Shimmer keyframe ─────────────────────────────────────────────────────────
const SHIMMER_STYLE_TAG = (
  <style>{`
    @keyframes shimmer {
      from { background-position: -400px 0; }
      to   { background-position: calc(400px + 100%) 0; }
    }
    .shimmer-shell {
      background: linear-gradient(90deg, #f0f0f0 25%, #e4e4e4 50%, #f0f0f0 75%);
      background-size: 400px 100%;
      animation: shimmer 1.5s infinite linear;
    }
    .shimmer-terminal {
      background: linear-gradient(90deg, #1a1a1a 25%, #222 50%, #1a1a1a 75%);
      background-size: 400px 100%;
      animation: shimmer 1.5s infinite linear;
    }
  `}</style>
);

// ─── SkeletonBlock ────────────────────────────────────────────────────────────
function SkeletonBlock({ width = '100%', height = 16, tone = 'shell', style: extraStyle = {} }) {
  return (
    <div
      className={tone === 'terminal' ? 'shimmer-terminal' : 'shimmer-shell'}
      style={{ width, height, flexShrink: 0, ...extraStyle }}
    />
  );
}

// ─── TableRowSkeleton ─────────────────────────────────────────────────────────
function TableRowSkeleton({ cols = 4, tone = 'shell' }) {
  const border = tone === 'terminal' ? '#111' : '#f5f5f5';
  const bg = tone === 'terminal' ? '#0a0a0a' : '#fff';
  const widths = ['60%', '80%', '50%', '40%', '30%'].slice(0, cols);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 12, padding: '12px 18px', borderBottom: `1px solid ${border}`, background: bg }}>
      {widths.map((w, i) => (
        <SkeletonBlock key={i} width={w} height={11} tone={tone} />
      ))}
    </div>
  );
}

// ─── HomePageSkeleton ─────────────────────────────────────────────────────────
function HomePageSkeleton() {
  return (
    <div style={{ background: '#fff' }}>
      {SHIMMER_STYLE_TAG}
      {/* Hero */}
      <div style={{ maxWidth: 1152, margin: '0 auto', padding: '72px 24px 64px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <SkeletonBlock width={120} height={10} />
          <SkeletonBlock width="90%" height={52} />
          <SkeletonBlock width="75%" height={52} />
          <SkeletonBlock width="60%" height={52} />
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <SkeletonBlock height={14} />
            <SkeletonBlock height={14} />
            <SkeletonBlock width="70%" height={14} />
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
            <SkeletonBlock width={140} height={40} />
            <SkeletonBlock width={120} height={40} />
          </div>
        </div>
        {/* HeroRegimeCard skeleton */}
        <div style={{ background: '#0a0a0a', border: '1px solid #1e1e1e', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
            <SkeletonBlock width={80} height={12} tone="terminal" />
            <SkeletonBlock width={40} height={12} tone="terminal" />
          </div>
          <SkeletonBlock width={140} height={36} tone="terminal" style={{ marginBottom: 16 }} />
          <SkeletonBlock width="100%" height={12} tone="terminal" style={{ marginBottom: 4 }} />
          <SkeletonBlock width="80%" height={12} tone="terminal" style={{ marginBottom: 20 }} />
          <SkeletonBlock width="100%" height={3} tone="terminal" style={{ marginBottom: 20 }} />
          {[0,1,2,3,4].map(i => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid #111' }}>
              <SkeletonBlock width={120} height={10} tone="terminal" />
              <SkeletonBlock width={40} height={10} tone="terminal" />
            </div>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      <div style={{ borderTop: '1px solid #e5e5e5', borderBottom: '1px solid #e5e5e5' }}>
        <div style={{ maxWidth: 1152, margin: '0 auto', padding: '0 24px', display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 0 }}>
          {[0,1,2,3].map(i => (
            <div key={i} style={{ padding: '22px', borderRight: i < 3 ? '1px solid #e5e5e5' : 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <SkeletonBlock width={60} height={28} />
              <SkeletonBlock width={100} height={10} />
            </div>
          ))}
        </div>
      </div>

      {/* Pair snapshot */}
      <div style={{ maxWidth: 1152, margin: '0 auto', padding: '64px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
          <SkeletonBlock width={200} height={22} />
          <SkeletonBlock width={100} height={32} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 1, background: '#e5e5e5' }}>
          {[0,1,2].map(i => (
            <div key={i} style={{ background: '#fff', padding: '20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <SkeletonBlock width={80} height={14} />
                <SkeletonBlock width={50} height={22} />
              </div>
              <SkeletonBlock width={120} height={22} />
              <SkeletonBlock width="80%" height={12} />
              <SkeletonBlock width="100%" height={3} />
              <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[0,1,2].map(j => (
                  <div key={j} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <SkeletonBlock width={80} height={10} />
                    <SkeletonBlock width={40} height={10} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── BriefPageSkeleton ────────────────────────────────────────────────────────
function BriefPageSkeleton() {
  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px' }}>
      {SHIMMER_STYLE_TAG}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 40, paddingBottom: 24, borderBottom: '1px solid #e5e5e5' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <SkeletonBlock width={120} height={10} />
          <SkeletonBlock width={280} height={32} />
        </div>
        <SkeletonBlock width={120} height={36} />
      </div>
      {/* Macro context */}
      <div style={{ background: '#fafafa', border: '1px solid #e5e5e5', borderLeft: '3px solid #e5e5e5', padding: '16px 20px', marginBottom: 40, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <SkeletonBlock width={120} height={10} />
        <SkeletonBlock height={13} />
        <SkeletonBlock width="80%" height={13} />
      </div>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 1, marginBottom: 32, borderBottom: '1px solid #e5e5e5', paddingBottom: 2 }}>
        {[0,1,2,3].map(i => <SkeletonBlock key={i} width={80} height={36} style={{ marginRight: 8 }} />)}
      </div>
      {/* Pair sections */}
      {[0,1,2].map(i => (
        <div key={i} style={{ border: '1px solid #e5e5e5', borderTop: '3px solid #e5e5e5', marginBottom: 16 }}>
          <div style={{ padding: '20px 24px', borderBottom: '1px solid #f0f0f0', background: '#fafafa', display: 'flex', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <SkeletonBlock width={80} height={14} />
              <SkeletonBlock width={200} height={12} />
            </div>
            <SkeletonBlock width={60} height={28} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', borderBottom: '1px solid #f0f0f0' }}>
            {[0,1,2,3,4].map(j => (
              <div key={j} style={{ padding: '14px 18px', borderRight: j < 4 ? '1px solid #f0f0f0' : 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                <SkeletonBlock width={60} height={9} />
                <SkeletonBlock width={50} height={14} />
              </div>
            ))}
          </div>
          <div style={{ padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <SkeletonBlock height={14} />
            <SkeletonBlock height={14} />
            <SkeletonBlock width="70%" height={14} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── PerformancePageSkeleton ──────────────────────────────────────────────────
function PerformancePageSkeleton() {
  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px' }}>
      {SHIMMER_STYLE_TAG}
      <div style={{ marginBottom: 40, paddingBottom: 24, borderBottom: '1px solid #e5e5e5', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <SkeletonBlock width={100} height={10} />
        <SkeletonBlock width={200} height={32} />
      </div>
      {/* Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 1, background: '#e5e5e5', marginBottom: 24 }}>
        {[0,1,2,3].map(i => (
          <div key={i} style={{ background: '#fff', padding: '22px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <SkeletonBlock width={100} height={9} />
            <SkeletonBlock width={80} height={30} />
            <SkeletonBlock width={120} height={10} />
          </div>
        ))}
      </div>
      {/* Equity curve */}
      <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between' }}>
          <SkeletonBlock width={200} height={10} />
          <SkeletonBlock width={60} height={22} />
        </div>
        <div style={{ padding: '16px 20px 8px' }}>
          <SkeletonBlock width="100%" height={120} />
          <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: 8 }}>
            {[0,1,2,3,4].map(i => <SkeletonBlock key={i} width={40} height={9} />)}
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', borderTop: '1px solid #f0f0f0' }}>
          {[0,1,2].map(i => (
            <div key={i} style={{ padding: '14px 18px', borderRight: i < 2 ? '1px solid #f0f0f0' : 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <SkeletonBlock width={60} height={11} />
              <SkeletonBlock width="100%" height={40} />
            </div>
          ))}
        </div>
      </div>
      {/* Table */}
      <div style={{ border: '1px solid #e5e5e5' }}>
        <div style={{ background: '#fafafa', padding: '10px 18px', borderBottom: '1px solid #e5e5e5', display: 'flex', gap: 8 }}>
          {['DATE','PAIR','CALL','OUTCOME','RET%'].map(h => <SkeletonBlock key={h} width={60} height={10} />)}
        </div>
        {[0,1,2,3,4,5].map(i => <TableRowSkeleton key={i} cols={5} tone="shell" />)}
      </div>
    </div>
  );
}

// ─── TerminalPairDeskSkeleton ─────────────────────────────────────────────────
function TerminalPairDeskSkeleton() {
  return (
    <div style={{ minHeight: '100vh', background: '#080808', color: '#e8e8e8' }}>
      {SHIMMER_STYLE_TAG}
      {/* Nav skeleton */}
      <div style={{ background: '#080808', borderBottom: '1px solid #1e1e1e', height: 76 }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <SkeletonBlock width={140} height={12} tone="terminal" />
          <div style={{ display: 'flex', gap: 8 }}>
            {[0,1,2].map(i => <SkeletonBlock key={i} width={80} height={28} tone="terminal" />)}
          </div>
        </div>
      </div>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>
        {/* Top strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 2, marginBottom: 2 }}>
          {[0,1,2,3].map(i => (
            <div key={i} style={{ background: '#0d0d0d', border: '1px solid #1e1e1e', padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <SkeletonBlock width={80} height={9} tone="terminal" />
              <SkeletonBlock width={120} height={30} tone="terminal" />
              <SkeletonBlock width="100%" height={3} tone="terminal" />
            </div>
          ))}
        </div>
        {/* Chips bar */}
        <div style={{ background: '#0c0c0c', border: '1px solid #1a1a1a', borderTop: 'none', padding: '10px 20px', marginBottom: 16, display: 'flex', gap: 8 }}>
          {[0,1,2,3].map(i => <SkeletonBlock key={i} width={100} height={26} tone="terminal" />)}
        </div>
        {/* Main grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 2 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {/* Tab bar */}
            <div style={{ display: 'flex', background: '#0a0a0a', borderBottom: '1px solid #1a1a1a', gap: 0 }}>
              {[0,1,2,3,4,5].map(i => <SkeletonBlock key={i} width={80} height={36} tone="terminal" style={{ marginRight: 2 }} />)}
            </div>
            {/* Table */}
            <div style={{ border: '1px solid #1a1a1a', borderTop: 'none' }}>
              {[0,1,2,3,4,5,6].map(i => <TableRowSkeleton key={i} cols={4} tone="terminal" />)}
            </div>
          </div>
          {/* Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {[100, 160, 80].map((h, i) => (
              <div key={i} style={{ border: '1px solid #1a1a1a', background: '#0c0c0c', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                <SkeletonBlock width={80} height={9} tone="terminal" />
                <SkeletonBlock width="100%" height={h} tone="terminal" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── CalendarPageSkeleton ─────────────────────────────────────────────────────
function CalendarPageSkeleton() {
  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px' }}>
      {SHIMMER_STYLE_TAG}
      {/* Header */}
      <div style={{ marginBottom: 40, paddingBottom: 24, borderBottom: '1px solid #e5e5e5', display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <SkeletonBlock width={120} height={10} />
          <SkeletonBlock width={240} height={32} />
          <SkeletonBlock width={360} height={14} />
        </div>
        <SkeletonBlock width={100} height={40} />
      </div>
      {/* FOMC banner */}
      <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', padding: '16px 20px', marginBottom: 32, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <div style={{ width: 4, background: '#2a2a2a', height: 40 }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <SkeletonBlock width={120} height={9} tone="terminal" />
            <SkeletonBlock width={200} height={15} tone="terminal" />
          </div>
        </div>
        <SkeletonBlock width={60} height={40} tone="terminal" />
      </div>
      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 28, borderBottom: '1px solid #e5e5e5', paddingBottom: 2 }}>
        {[0,1,2,3].map(i => <SkeletonBlock key={i} width={70} height={36} />)}
      </div>
      {/* Event rows */}
      {[0,1,2,3,4].map(i => (
        <div key={i} style={{ border: '1px solid #e5e5e5', borderBottom: 'none', display: 'grid', gridTemplateColumns: '100px 1fr' }}>
          <div style={{ padding: '16px', borderRight: '1px solid #f0f0f0', background: '#fafafa', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <SkeletonBlock width={30} height={9} />
            <SkeletonBlock width={60} height={12} />
            <SkeletonBlock width={25} height={9} />
          </div>
          <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e5e5e5' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
              <SkeletonBlock width="60%" height={13} />
              <SkeletonBlock width="30%" height={9} />
            </div>
            <SkeletonBlock width={40} height={9} />
          </div>
        </div>
      ))}
      <div style={{ border: '1px solid #e5e5e5', padding: '12px 20px' }}><SkeletonBlock width={300} height={10} /></div>
    </div>
  );
}

// ─── PairDetailSkeleton ───────────────────────────────────────────────────────
function PairDetailSkeleton() {
  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px' }}>
      {SHIMMER_STYLE_TAG}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 32, marginBottom: 40, paddingBottom: 24, borderBottom: '1px solid #e5e5e5' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <SkeletonBlock width={140} height={10} />
          <SkeletonBlock width={220} height={40} />
          <SkeletonBlock width={160} height={22} />
        </div>
        <SkeletonBlock width={160} height={40} />
      </div>
      {/* 2-col grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        {[0,1].map(i => (
          <div key={i} style={{ border: '1px solid #e5e5e5', borderTop: '3px solid #e5e5e5' }}>
            <div style={{ padding: '14px 20px', background: '#fafafa', borderBottom: '1px solid #f0f0f0' }}>
              <SkeletonBlock width={120} height={10} />
            </div>
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <SkeletonBlock width="80%" height={13} />
              <SkeletonBlock width="100%" height={3} />
              {[0,1,2].map(j => (
                <div key={j} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <SkeletonBlock width={100} height={10} />
                  <SkeletonBlock width={50} height={10} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {/* Events row */}
      <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
        <div style={{ padding: '14px 20px', background: '#fafafa', borderBottom: '1px solid #f0f0f0' }}>
          <SkeletonBlock width={200} height={10} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)' }}>
          {[0,1,2].map(i => (
            <div key={i} style={{ padding: '16px 20px', borderRight: i < 2 ? '1px solid #f0f0f0' : 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <SkeletonBlock width={80} height={9} />
              <SkeletonBlock width="90%" height={13} />
              <SkeletonBlock width={80} height={10} />
            </div>
          ))}
        </div>
      </div>
      {/* Heatmap */}
      <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
        <div style={{ padding: '14px 20px', background: '#fafafa', borderBottom: '1px solid #f0f0f0' }}>
          <SkeletonBlock width={180} height={10} />
        </div>
        <div style={{ padding: '16px 20px', display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          {Array.from({ length: 30 }, (_, i) => (
            <div key={i} style={{ width: 20, height: 20, background: '#f0f0f0' }} />
          ))}
        </div>
      </div>
      {/* Table */}
      <div style={{ border: '1px solid #e5e5e5' }}>
        {[0,1,2,3].map(i => <TableRowSkeleton key={i} cols={5} tone="shell" />)}
      </div>
    </div>
  );
}

// ─── SkeletonDemo ─────────────────────────────────────────────────────────────
function SkeletonDemo({ navigate }) {
  const SECTIONS = [
    { label: 'Home Page', component: <HomePageSkeleton /> },
    { label: 'Brief Page', component: <BriefPageSkeleton /> },
    { label: 'Performance Page', component: <PerformancePageSkeleton /> },
    { label: 'Calendar Page', component: <CalendarPageSkeleton /> },
    { label: 'Pair Detail', component: <PairDetailSkeleton /> },
    { label: 'Terminal Pair Desk (Dark)', component: <TerminalPairDeskSkeleton /> },
  ];
  const [active, setActive] = React.useState(0);

  return (
    <div style={{ minHeight: '100vh', background: '#fafafa' }}>
      {SHIMMER_STYLE_TAG}
      <div style={{ background: '#0a0a0a', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#555', letterSpacing: '0.1em' }}>LOADING STATES DEMO</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>Shimmer skeleton review</span>
        </div>
        {navigate && (
          <button onClick={() => navigate('/')} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#555', border: '1px solid #1e1e1e', padding: '6px 12px', background: 'none', cursor: 'pointer' }}>← Shell</button>
        )}
      </div>
      {/* Tab strip */}
      <div style={{ display: 'flex', background: '#fff', borderBottom: '1px solid #e5e5e5', overflowX: 'auto' }}>
        {SECTIONS.map((s, i) => (
          <button key={i} onClick={() => setActive(i)}
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '12px 16px', color: active === i ? '#0a0a0a' : '#aaa', borderBottom: active === i ? '2px solid #F5923A' : '2px solid transparent', marginBottom: -1, whiteSpace: 'nowrap', fontWeight: active === i ? 700 : 400, letterSpacing: '0.06em', background: 'none', cursor: 'pointer' }}>
            {s.label.toUpperCase()}
          </button>
        ))}
      </div>
      <div style={{ border: '2px dashed #e5e5e5', margin: '24px', padding: '2px' }}>
        <div style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', padding: '8px 14px' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.1em' }}>SKELETON PREVIEW — {SECTIONS[active].label.toUpperCase()}</span>
        </div>
        {SECTIONS[active].component}
      </div>
    </div>
  );
}

Object.assign(window, {
  SkeletonBlock, TableRowSkeleton,
  HomePageSkeleton, BriefPageSkeleton, PerformancePageSkeleton,
  TerminalPairDeskSkeleton, CalendarPageSkeleton, PairDetailSkeleton,
  SkeletonDemo,
});
