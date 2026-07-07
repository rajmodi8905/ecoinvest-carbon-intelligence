import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import StatCard from '../components/StatCard';
import TerminalTable from '../components/TerminalTable';
import * as api from '../services/api';

const fmtPrice = v => v ? `$${parseFloat(v).toFixed(2)}` : '—';
const fmtChg   = v => { const n = parseFloat(v); return <span className={`mono ${n>=0?'pos':'neg'}`}>{n>=0?'+':''}{n.toFixed(2)}%</span>; };
const fmtNum   = (v, d=3) => v != null ? parseFloat(v).toFixed(d) : '—';

const COL_DEFS = [
  { key: 'ticker',         label: 'TICKER',    width: 72,
    render: v => <span className="mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{v}</span> },
  { key: 'company_name',   label: 'COMPANY',   width: '1fr', sortable: false,
    render: v => <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis' }}>{v}</span> },
  { key: 'price',          label: 'LAST',      width: 80,  align: 'right',
    render: v => <span className="mono">{fmtPrice(v)}</span> },
  { key: 'change_percent', label: 'CHG%',      width: 72,  align: 'right', render: fmtChg },
  { key: 'risk',           label: 'RISK▼',     width: 65,  align: 'right',
    render: v => { const n=parseFloat(v); return <span className="mono" style={{color: n>0.4?'var(--red)':n>0.2?'var(--amber)':'var(--green)'}}>{n.toFixed(3)}</span>; } },
  { key: 'impact_rating',  label: 'IMPACT',    width: 65,  align: 'right',
    render: v => { const n=parseFloat(v); return <span className="mono" style={{color: n>80?'var(--green)':n>60?'var(--amber)':'var(--red)'}}>{n.toFixed(1)}</span>; } },
  { key: 'policy_alignment',label: 'POLICY',   width: 70,  align: 'right',
    render: v => { const n=parseFloat(v); return <span className="mono" style={{color: n>80?'var(--green)':n>50?'var(--amber)':'var(--red)'}}>{n.toFixed(1)}%</span>; } },
  { key: 'momentum',       label: 'MOMENTUM',  width: 85,  align: 'right',
    render: v => { const n=parseFloat(v); return <span className="mono" style={{color:n>0?'var(--green)':n<0?'var(--red)':'var(--text-muted)'}}>{n>=0?'+':''}{n.toFixed(3)}</span>; } },
  { key: 'news_24h',       label: '24H NEWS',  width: 75,  align: 'right',
    render: v => <span className="mono">{v}</span> },
  { key: 'sentiment_24h',  label: 'SENT 24H',  width: 80,  align: 'right',
    render: v => { const n=parseFloat(v); return <span className="mono" style={{color:n>0?'var(--green)':n<0?'var(--red)':'var(--text-muted)'}}>{n>=0?'+':''}{n.toFixed(3)}</span>; } },
];

const CompaniesPage = () => {
  const navigate = useNavigate();
  const [all, setAll] = React.useState([]);
  const [search, setSearch] = React.useState('');
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch('http://localhost:5001/api/analytics/top-movers')
      .then(r => r.json())
      .then(d => { if (d.companies) setAll(d.companies); setLoading(false); })
      .catch(() => setLoading(false));

    api.onDataUpdate('finance', () => {
      fetch('http://localhost:5001/api/analytics/top-movers')
        .then(r => r.json())
        .then(d => { if (d.companies) setAll(d.companies); })
        .catch(() => {});
    });
  }, []);

  const filtered = React.useMemo(() => {
    if (!search) return all;
    const q = search.toLowerCase();
    return all.filter(c =>
      c.ticker?.toLowerCase().includes(q) ||
      c.company_name?.toLowerCase().includes(q) ||
      c.industry?.toLowerCase().includes(q)
    );
  }, [all, search]);

  // KPIs
  const avgRisk  = all.length ? (all.reduce((s,c) => s + (c.risk||0), 0) / all.length).toFixed(3) : '—';
  const highRisk = all.filter(c => c.risk > 0.4).length;
  const avgSent  = all.length ? (all.reduce((s,c) => s + (c.sentiment_24h||0), 0) / all.length).toFixed(3) : '—';
  const topMover = all.length ? all.reduce((a,b) => Math.abs(b.change_percent||0) > Math.abs(a.change_percent||0) ? b : a, all[0]) : null;

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100%' }}>
      <div className="page-header">
        <h1>Companies</h1>
        <p>Carbon-exposed equities — click any row for a live signals report + AI analysis</p>
      </div>
      <div className="page-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="stat-grid">
          <StatCard label="Companies Tracked" value={all.length} sublabel="carbon-exposed equities" />
          <StatCard label="Avg Risk Score"     value={avgRisk}   sublabel="composite market risk" valueColor={parseFloat(avgRisk)>0.3?'var(--red)':'var(--green)'} />
          <StatCard label="High Risk"          value={highRisk}  sublabel="risk score > 0.4" valueColor={highRisk>5?'var(--red)':'var(--amber)'} />
          <StatCard label="Avg Sentiment 24H"  value={avgSent}   sublabel="rolling mean across companies" valueColor={parseFloat(avgSent)>=0?'var(--green)':'var(--red)'} />
        </div>

        <div className="panel">
          <div className="toolbar">
            <div className="terminal-search" style={{ flex: 1, maxWidth: 300 }}>
              <Search size={12} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search ticker, company, or industry..."
              />
            </div>
            {topMover && (
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                Top mover: <span className="mono" style={{ color: 'var(--text-secondary)' }}>{topMover.ticker}</span>{' '}
                <span className={`mono ${(topMover.change_percent||0)>=0?'pos':'neg'}`}>
                  {(topMover.change_percent||0)>=0?'+':''}{(topMover.change_percent||0).toFixed(2)}%
                </span>
              </span>
            )}
          </div>

          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>Loading company data...</div>
          ) : (
            <TerminalTable
              columns={COL_DEFS}
              data={filtered}
              defaultSort="risk"
              defaultDir="desc"
              onRowClick={row => navigate(`/report/${row.ticker}`)}
              maxHeight="calc(100vh - 360px)"
              emptyMessage={search ? 'No companies match your search' : 'No company data available'}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default CompaniesPage;
