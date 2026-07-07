import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import StatCard from '../components/StatCard';
import TerminalTable from '../components/TerminalTable';

const fmtNum = (v, d=3) => v != null ? parseFloat(v).toFixed(d) : '—';

const COLS = [
  { key: 'theme',           label: 'THEME',          width: '1fr',  sortable: true,
    render: v => <span style={{ fontWeight: 500 }}>{v}</span> },
  { key: 'articles_24h',   label: '24H ARTICLES▼',  width: 110,    align: 'right', sortable: true,
    render: v => <span className="mono">{v}</span> },
  { key: 'articles_1h',    label: '1H',              width: 50,     align: 'right', sortable: true,
    render: v => <span className="mono">{v}</span> },
  { key: 'sentiment',      label: 'SENTIMENT',       width: 85,     align: 'right', sortable: true,
    render: v => { const n=parseFloat(v); return <span className="mono" style={{color:n>0?'var(--green)':n<0?'var(--red)':'var(--text-muted)'}}>{n>=0?'+':''}{n.toFixed(3)}</span>; } },
  { key: 'momentum',       label: 'MOMENTUM',        width: 85,     align: 'right', sortable: true,
    render: v => { const n=parseFloat(v); return <span className="mono" style={{color:n>0?'var(--green)':n<0?'var(--red)':'var(--text-muted)'}}>{n>=0?'+':''}{n.toFixed(3)}</span>; } },
  { key: 'impact',         label: 'IMPACT',          width: 70,     align: 'right', sortable: true,
    render: v => <span className="mono" style={{ color: parseFloat(v)>80?'var(--green)':parseFloat(v)>50?'var(--amber)':'var(--red)' }}>{fmtNum(v, 1)}</span> },
  { key: 'latest_headline',label: 'LATEST HEADLINE', width: '2fr',  sortable: false,
    render: v => <span style={{ color:'var(--text-muted)', fontSize:'11px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{v}</span> },
];

const MacroPage = () => {
  const navigate = useNavigate();
  const [data, setData] = React.useState(null);
  const [search, setSearch] = React.useState('');
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch('http://localhost:5001/api/analytics/macro-themes')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const themes = data?.themes || [];
  const filtered = search
    ? themes.filter(t => t.theme.toLowerCase().includes(search.toLowerCase()) || t.latest_headline?.toLowerCase().includes(search.toLowerCase()))
    : themes;

  const hottest = data?.hottest_theme || '—';
  const avgSent = data?.avg_sentiment != null ? data.avg_sentiment.toFixed(3) : '—';

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100%' }}>
      <div className="page-header">
        <h1>Macro Themes</h1>
        <p>Climate / policy narratives tracked across the live news stream — click any row for detail</p>
      </div>
      <div className="page-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="stat-grid">
          <StatCard label="Themes Tracked"  value={data?.total_themes ?? '—'}         sublabel="active narrative clusters" />
          <StatCard label="24H Articles"    value={data?.total_articles_24h ?? '—'}   sublabel="across all themes" />
          <StatCard label="Highest Impact"  value={hottest}                            sublabel="max relevance" valueColor="var(--amber)" />
          <StatCard label="Avg Sentiment"   value={avgSent}
            sublabel="rolling mean"
            valueColor={parseFloat(avgSent)>=0?'var(--green)':'var(--red)'}
          />
        </div>

        <div className="panel">
          <div className="toolbar">
            <div className="terminal-search" style={{ flex: 1, maxWidth: 300 }}>
              <Search size={12} />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search theme..." />
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
              Impact ≥ 80 = <span className="amb">HIGH RELEVANCE</span>
            </span>
          </div>
          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>Loading macro themes...</div>
          ) : (
            <TerminalTable
              columns={COLS}
              data={filtered}
              defaultSort="articles_24h"
              defaultDir="desc"
              onRowClick={row => navigate(`/macro/${encodeURIComponent(row.theme)}`)}
              maxHeight="calc(100vh - 360px)"
              emptyMessage="No themes available"
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default MacroPage;
