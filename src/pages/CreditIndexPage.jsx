import React from 'react';
import { Link } from 'react-router-dom';
import StatCard from '../components/StatCard';
import TerminalTable from '../components/TerminalTable';

const fmtUSD = v => v ? `$${parseFloat(v).toFixed(4)}` : '—';
const fmtM   = v => v ? `$${(parseFloat(v)/1e6).toFixed(2)}M` : '—';
const fmtNum = v => v != null ? Number(v).toLocaleString() : '—';

const COLS = [
  { key: 'category',      label: 'CATEGORY',    width: '1fr',  sortable: true,
    render: v => <span style={{ fontWeight: 500 }}>{v}</span> },
  { key: 'floor',         label: 'FLOOR $/T',   width: 90,     align: 'right', sortable: true,
    render: v => <span className="mono pos">{fmtUSD(v)}</span> },
  { key: 'avg',           label: 'AVG $/T',     width: 90,     align: 'right', sortable: true,
    render: v => <span className="mono">{fmtUSD(v)}</span> },
  { key: 'max',           label: 'MAX $/T',     width: 90,     align: 'right', sortable: true,
    render: v => <span className="mono">{fmtUSD(v)}</span> },
  { key: 'supply',        label: 'SUPPLY',      width: 100,    align: 'right', sortable: true,
    render: v => <span className="mono">{fmtNum(v)}</span> },
  { key: 'market_value',  label: 'MARKET VALUE',width: 110,    align: 'right', sortable: true,
    render: v => <span className="mono">{fmtM(v)}</span> },
  { key: 'project_count', label: 'PROJECTS',    width: 80,     align: 'right', sortable: true,
    render: v => <span className="mono">{v}</span> },
  { key: 'listing_count', label: 'LISTINGS',    width: 80,     align: 'right', sortable: true,
    render: v => <span className="mono">{v}</span> },
];

const CreditIndexPage = () => {
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch('http://localhost:5001/api/analytics/credit-index')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const index = data?.index || [];

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100%' }}>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Link to="/" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>← Dashboard</Link>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>/</span>
          <span style={{ fontSize: '11px', color: 'var(--green)' }}>Credit Index</span>
        </div>
        <h1>Carbon Credit Index</h1>
        <p>VCM benchmark by category — Verra VCS registry metadata + live Carbonmark prices</p>
      </div>

      <div className="page-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* KPI cards */}
        <div className="stat-grid">
          <StatCard
            label="Market Floor"
            value={data?.market_floor ? `$${data.market_floor}` : '—'}
            sublabel="cheapest traded credit"
            valueColor="var(--green)"
          />
          <StatCard
            label="Total Market Value"
            value={data?.total_market_value ? `$${(data.total_market_value/1e6).toFixed(2)}M` : '—'}
            sublabel="Σ best-ask × supply"
          />
          <StatCard
            label="Traded Projects"
            value={data?.traded_projects ?? '—'}
            sublabel="with live Carbonmark listings"
          />
          <StatCard
            label="Categories"
            value={data?.total_categories ?? '—'}
            sublabel="index constituents"
          />
        </div>

        {/* Index table */}
        <div className="panel">
          <div className="panel-header">
            <h3>Index Constituents</h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {index.length} categories · sorted by market value
            </span>
          </div>
          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              Loading index data...
            </div>
          ) : (
            <TerminalTable
              columns={COLS}
              data={index}
              defaultSort="market_value"
              defaultDir="desc"
              maxHeight="calc(100vh - 340px)"
              emptyMessage="No index data available"
            />
          )}
        </div>

        <p style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Prices are real per-tonne best-asks aggregated from Carbonmark marketplace listings joined to the Verra VCS project registry.
          Floor = lowest traded price in category. Avg = mean price across all priced projects. Supply = sum of available credits.
          Market Value = Σ(price × available_credits) for all priced projects.
        </p>
      </div>
    </div>
  );
};

export default CreditIndexPage;
