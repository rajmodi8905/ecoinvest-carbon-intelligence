import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import TerminalTable from '../components/TerminalTable';
import * as api from '../services/api';

const fmtPrice = v => v ? `$${parseFloat(v).toFixed(4)}` : null;

const STATUS_CELL = (val, row) => {
  const traded = (row.listing_count > 0) || (parseFloat(row.amount || 0) > 0);
  return (
    <span className={`badge ${traded ? 'badge-green' : 'badge-muted'}`}>
      {traded ? 'Traded' : 'Registry'}
    </span>
  );
};

const COLS = [
  { key: 'project_name',    label: 'PROJECT',   width: '2fr',  sortable: false,
    render: (v,row) => <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis' }}>{v || row.name}</span> },
  { key: 'category',        label: 'CATEGORY',  width: 120, sortable: true,
    render: v => <span className="badge badge-blue" style={{ fontSize: '10px' }}>{v || 'Other'}</span> },
  { key: 'country',         label: 'COUNTRY',   width: 90, sortable: true,
    render: v => <span style={{ color: 'var(--text-secondary)' }}>{v || '—'}</span> },
  { key: 'price',           label: 'SPOT $/T',  width: 85,  align: 'right', sortable: true,
    render: v => <span className="mono pos">{fmtPrice(v) || '—'}</span> },
  { key: 'available_credits',label: 'SUPPLY',   width: 90,  align: 'right', sortable: true,
    render: v => <span className="mono">{v ? Number(v).toLocaleString() : '—'}</span> },
  { key: 'vintage',         label: 'VINTAGE',   width: 70,  align: 'right', sortable: true,
    render: v => <span className="mono">{v || '—'}</span> },
  { key: 'registry_status', label: 'STATUS',    width: 80,  sortable: true,
    render: STATUS_CELL },
];

const ProjectsPage = () => {
  const navigate = useNavigate();
  const [all, setAll] = React.useState([]);
  const [search, setSearch] = React.useState('');
  const [category, setCategory] = React.useState('All');
  const [filter, setFilter] = React.useState('All');
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    api.getProjects({ limit: 5000 })
      .then(d => { setAll(Array.isArray(d) ? d : d?.data || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const categories = React.useMemo(() => {
    const s = new Set(all.map(p => p.category).filter(Boolean));
    return ['All', ...Array.from(s).sort()];
  }, [all]);

  const filtered = React.useMemo(() => {
    let list = all;
    if (category !== 'All') list = list.filter(p => p.category === category);
    if (filter === 'Traded') list = list.filter(p => parseFloat(p.price || 0) > 0);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(p =>
        p.project_name?.toLowerCase().includes(q) ||
        p.project_id?.toLowerCase().includes(q) ||
        p.country?.toLowerCase().includes(q)
      );
    }
    return list;
  }, [all, category, filter, search]);

  const traded = all.filter(p => parseFloat(p.price || 0) > 0).length;

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100%' }}>
      <div className="page-header">
        <h1>Carbon Projects</h1>
        <p>{all.length.toLocaleString()} Verra VCS projects · {traded} traded on Carbonmark — click any for its AI report</p>
      </div>
      <div className="page-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="panel">
          <div className="toolbar" style={{ gap: 8 }}>
            <div className="terminal-search" style={{ flex: 1, maxWidth: 280 }}>
              <Search size={12} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search name, VCS ID, or country..."
              />
            </div>
            <select className="terminal-select" value={category} onChange={e => setCategory(e.target.value)}>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            {['All','Traded'].map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                padding: '4px 10px', fontSize: '11px', borderRadius: 'var(--radius-sm)',
                border: `1px solid ${filter===f?'var(--green)':'var(--border)'}`,
                background: filter===f?'var(--green-dim)':'none',
                color: filter===f?'var(--green)':'var(--text-muted)',
                cursor: 'pointer', transition: 'all 120ms',
              }}>{f}</button>
            ))}
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
              {filtered.length.toLocaleString()} projects
            </span>
          </div>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>Loading projects...</div>
          ) : (
            <TerminalTable
              columns={COLS}
              data={filtered}
              defaultSort="price"
              defaultDir="desc"
              onRowClick={row => navigate(`/report/${row.project_id || row.id}`)}
              maxHeight="calc(100vh - 260px)"
              emptyMessage={search || category !== 'All' ? 'No projects match your filters' : 'No project data available'}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ProjectsPage;
