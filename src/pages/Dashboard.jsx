import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import * as api from '../services/api';
import StatCard from '../components/StatCard';
import TerminalTable from '../components/TerminalTable';
import SentimentBadge from '../components/SentimentBadge';

import { fmtTickerPrice } from '../utils/currency';

const fmtPrice = v => v ? `$${parseFloat(v).toFixed(2)}` : '—'; // for carbon credit prices (always USD)

const fmtChg   = v => {
  const n = parseFloat(v);
  return <span className={n >= 0 ? 'pos mono' : 'neg mono'}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</span>;
};
const fmtNum   = v => v != null ? parseFloat(v).toFixed(3) : '—';
const fmtK     = v => {
  const n = parseInt(v);
  return n >= 1000 ? `${(n/1000).toFixed(1)}K` : String(n);
};

// ── Index mini-table columns ─────────────────────────────────────────────────
const INDEX_COLS = [
  { key: 'category',      label: 'CATEGORY',   width: '1fr',  sortable: false },
  { key: 'floor',         label: 'FLOOR $/T',  width: 80,     align: 'right', render: v => <span className="mono pos">{v ? `$${v}` : '—'}</span> },
  { key: 'avg',           label: 'AVG $/T',    width: 75,     align: 'right', render: v => <span className="mono">{v ? `$${v}` : '—'}</span> },
  { key: 'project_count', label: 'PROJ',       width: 50,     align: 'right', render: v => <span className="mono">{v}</span> },
  { key: 'market_value',  label: 'MKT VALUE',  width: 90,     align: 'right', render: v => <span className="mono">{v ? `$${(v/1e6).toFixed(2)}M` : '—'}</span> },
];

// ── Top movers columns ────────────────────────────────────────────────────────
const MOVER_COLS = [
  { key: 'ticker',         label: 'TICKER', width: 70, render: (v, row) => (
      <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
        {v} {row?.pathway_computed && <span title="Live analytics powered by Pathway" style={{ fontSize: '11px' }}>⚡</span>}
      </span>
  ) },
  { key: 'price',          label: 'LAST',   width: 72, align: 'right', render: (v, row) => <span className="mono">{fmtTickerPrice(v, row?.ticker)}</span> },

  { key: 'change_percent', label: 'CHG%',   width: 70, align: 'right', render: fmtChg },
  { key: 'risk',           label: 'RISK',   width: 55, align: 'right', render: v => {
    const n = parseFloat(v);
    const col = n > 0.4 ? 'var(--red)' : n > 0.2 ? 'var(--amber)' : 'var(--green)';
    return <span className="mono" style={{ color: col }}>{n.toFixed(3)}</span>;
  }},
];

// ── News row ──────────────────────────────────────────────────────────────────
const NewsRow = ({ article }) => {
  const sentColor = article.sentiment === 'Positive' ? 'var(--green)'
    : article.sentiment === 'Negative' ? 'var(--red)' : 'var(--text-muted)';
  return (
    <a href={article.link} target="_blank" rel="noopener noreferrer"
      style={{
        display: 'block', padding: '8px 14px',
        borderBottom: '1px solid var(--border-subtle)',
        transition: 'background 120ms',
      }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-hover)'}
      onMouseLeave={e => e.currentTarget.style.background = 'none'}
    >
      <div style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.4, marginBottom: 3 }}>
        {article.title}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        <span className="mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
          {article.published ? article.published.slice(0,5) : ''}
        </span>
        <span className="badge badge-muted">{article.source}</span>
        <span style={{ fontSize: '10px', color: sentColor, fontFamily: 'var(--mono)' }}>
          {article.sentiment}
        </span>
      </div>
    </a>
  );
};

// ── Event row (SURGE) ─────────────────────────────────────────────────────────
const EventRow = ({ theme, onClick }) => (
  <div
    onClick={onClick}
    style={{
      display: 'grid',
      gridTemplateColumns: '50px 1fr 60px 55px 50px',
      alignItems: 'center',
      padding: '7px 14px',
      borderBottom: '1px solid var(--border-subtle)',
      cursor: 'pointer',
      transition: 'background 120ms',
      gap: 8,
    }}
    onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-hover)'}
    onMouseLeave={e => e.currentTarget.style.background = 'none'}
  >
    <span className="surge-tag">HOT</span>
    <span style={{ fontSize: '12px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
      {theme.theme}
    </span>
    <span className="mono" style={{ fontSize: '11px', color: 'var(--amber)', textAlign: 'right' }}>
      {theme.impact?.toFixed(1)}
    </span>
    <span className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'right' }}>
      {theme.articles_24h}
    </span>
    <span className="row-arrow">›</span>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────

const Dashboard = () => {
  const navigate = useNavigate();

  const [analytics, setAnalytics] = React.useState(null);
  const [indexData, setIndexData]  = React.useState([]);
  const [movers,    setMovers]     = React.useState([]);
  const [news,      setNews]       = React.useState([]);
  const [events,    setEvents]     = React.useState([]);

  const load = React.useCallback(async () => {
    try {
      const [an, ix, mv, nw, mt] = await Promise.all([
        api.getAnalytics().catch(() => null),
        fetch('http://localhost:5001/api/analytics/credit-index').then(r => r.json()).catch(() => null),
        fetch('http://localhost:5001/api/analytics/top-movers').then(r => r.json()).catch(() => null),
        api.getNews({ limit: 6 }).catch(() => null),
        fetch('http://localhost:5001/api/analytics/macro-themes').then(r => r.json()).catch(() => null),
      ]);
      if (an) setAnalytics(an);
      if (ix?.index) setIndexData(ix.index.slice(0, 6));
      if (mv?.companies) setMovers(mv.companies.slice(0, 6));
      if (nw?.data) setNews(nw.data);
      if (mt?.themes) {
        // High-impact based on new impact score
        const sorted = [...mt.themes].sort((a, b) => (b.impact || 0) - (a.impact || 0));
        setEvents(sorted.slice(0, 5));
      }
    } catch (e) {
      console.error('Dashboard load error', e);
    }
  }, []);

  React.useEffect(() => {
    load();
    // Refresh on WebSocket data update
    api.onDataUpdate('data_update', load);
    return () => api.onDataUpdate('data_update', null);
  }, [load]);

  // ── Derived KPIs ─────────────────────────────────────────────────────────
  const proj   = analytics?.projects || {};
  const fin    = analytics?.finance  || {};
  const newsAn = analytics?.news     || {};
  const pos    = newsAn.by_sentiment?.positive ?? 0;
  const neu    = newsAn.by_sentiment?.neutral  ?? 0;
  const neg    = newsAn.by_sentiment?.negative ?? 0;

  // VCM floor: min of all index category floors
  const vcmFloor = indexData.length
    ? Math.min(...indexData.map(i => i.floor).filter(f => f > 0))
    : null;

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100%' }}>
      {/* Page header */}
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Live voluntary carbon market intelligence — registry, marketplace, equities, news</p>
      </div>

      <div className="page-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* KPI row */}
        <div className="stat-grid">
          <StatCard
            label="VCM Floor $/tCO₂e"
            value={vcmFloor ? `$${vcmFloor.toFixed(4)}` : '—'}
            sublabel={`${indexData.reduce((a,i) => a + (i.listing_count||0), 0)} traded listings · ${indexData.length} categories`}
            valueColor="var(--green)"
          />
          <StatCard
            label="Carbon Projects"
            value={fmtK(proj.total || 0)}
            sublabel="Verra VCS registry"
          />
          <StatCard
            label="Companies Tracked"
            value={fin.total_tickers || 0}
            sublabel="carbon-exposed equities"
          />
          <StatCard
            label="News Sentiment"
            value={
              <span style={{ fontFamily: 'var(--mono)', fontSize: 22 }}>
                <span className="pos">{pos}▲</span>{' '}
                <span style={{ color: 'var(--text-muted)' }}>{neu}■</span>{' '}
                <span className="neg">{neg}▼</span>
              </span>
            }
            sublabel={`${(pos+neu+neg)} recent articles`}
          />
        </div>

        {/* Row 2: Credit Index mini + Top Movers */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="panel">
            <div className="panel-header">
              <h3>Carbon Credit Index</h3>
              <Link to="/index" style={{ color: 'var(--green)', fontSize: '11px' }}>Full Index →</Link>
            </div>
            <TerminalTable
              columns={INDEX_COLS}
              data={indexData}
              onRowClick={row => navigate(`/index`)}
              maxHeight="240px"
              emptyMessage="Loading index data..."
            />
          </div>
          <div className="panel">
            <div className="panel-header">
              <h3>Top Movers</h3>
              <Link to="/companies" style={{ color: 'var(--green)', fontSize: '11px' }}>All companies →</Link>
            </div>
            <TerminalTable
              columns={MOVER_COLS}
              data={movers}
              onRowClick={row => navigate(`/report/${row.ticker}`)}
              maxHeight="240px"
              emptyMessage="Loading company data..."
            />
          </div>
        </div>

        {/* Row 3: Live News + High-Impact Events */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="panel">
            <div className="panel-header">
              <h3>Live News</h3>
              <Link to="/news" style={{ color: 'var(--green)', fontSize: '11px' }}>All news →</Link>
            </div>
            <div>
              {news.length === 0 && (
                <div style={{ padding: '28px 14px', color: 'var(--text-muted)', fontSize: '12px', textAlign: 'center' }}>
                  Loading news feed...
                </div>
              )}
              {news.slice(0, 10).map((a, i) => <NewsRow key={a.id || i} article={a} />)}
              {news.length > 10 && (
                <div style={{ padding: '12px', textAlign: 'center', borderTop: '1px solid var(--border-subtle)' }}>
                  <Link to="/news" style={{ fontSize: '12px', color: 'var(--text-secondary)', transition: 'color 120ms' }} onMouseEnter={e => e.currentTarget.style.color = 'var(--green)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}>
                    View All News →
                  </Link>
                </div>
              )}
            </div>
          </div>
          <div className="panel">
            <div className="panel-header">
              <h3>High-Impact Events</h3>
              <Link to="/macro" style={{ color: 'var(--green)', fontSize: '11px' }}>Macro themes →</Link>
            </div>
            {/* Column header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '50px 1fr 60px 55px 50px',
              padding: '5px 14px',
              borderBottom: '1px solid var(--border)',
              gap: 8,
            }}>
              {['TYPE','THEME','VEL','24H ART',''].map((h,i) => (
                <span key={i} style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em', textAlign: i >= 2 ? 'right' : 'left' }}>{h}</span>
              ))}
            </div>
            {events.length === 0 && (
              <div style={{ padding: '28px 14px', color: 'var(--text-muted)', fontSize: '12px', textAlign: 'center' }}>
                No surge events detected
              </div>
            )}
            {events.map((e, i) => (
              <EventRow key={i} theme={e} onClick={() => navigate(`/macro/${encodeURIComponent(e.theme)}`)} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
