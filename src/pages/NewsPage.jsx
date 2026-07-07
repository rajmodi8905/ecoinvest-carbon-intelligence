import React from 'react';
import { Search } from 'lucide-react';
import SentimentBadge from '../components/SentimentBadge';

const SENTIMENTS = ['All', 'Positive', 'Neutral', 'Negative'];

const NewsPage = () => {
  const [all, setAll] = React.useState([]);
  const [search, setSearch] = React.useState('');
  const [sentiment, setSentiment] = React.useState('All');
  const [source, setSource] = React.useState('All');
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch('http://localhost:5001/api/news?limit=1000')
      .then(r => r.json())
      .then(d => { setAll(d.data || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const sources = React.useMemo(() => {
    const s = new Set(all.map(a => a.source).filter(Boolean));
    return ['All', ...Array.from(s).sort()];
  }, [all]);

  const filtered = React.useMemo(() => {
    let list = all;
    if (sentiment !== 'All') list = list.filter(a => a.sentiment === sentiment);
    if (source   !== 'All') list = list.filter(a => a.source === source);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(a =>
        a.title?.toLowerCase().includes(q) ||
        a.source?.toLowerCase().includes(q) ||
        a.summary?.toLowerCase().includes(q)
      );
    }
    return list;
  }, [all, sentiment, source, search]);

  const sentColor = s => s==='Positive'?'var(--green)':s==='Negative'?'var(--red)':'var(--text-muted)';

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100%' }}>
      <div className="page-header">
        <h1>News</h1>
        <p>Live market intelligence — {all.length} articles · sentiment-tagged in real time</p>
      </div>
      <div className="page-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {/* Sentiment filter */}
          {SENTIMENTS.map(s => (
            <button key={s} onClick={() => setSentiment(s)} style={{
              padding: '4px 10px', fontSize: '11px', borderRadius: 'var(--radius-sm)',
              border: `1px solid ${sentiment===s?'var(--green)':'var(--border)'}`,
              background: sentiment===s?'var(--green-dim)':'none',
              color: sentiment===s?'var(--green)':'var(--text-muted)',
              cursor: 'pointer', transition: 'all 120ms',
            }}>{s}</button>
          ))}
          <select className="terminal-select" value={source} onChange={e => setSource(e.target.value)}>
            {sources.slice(0, 50).map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <div className="terminal-search" style={{ flex: 1, maxWidth: 320 }}>
            <Search size={12} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search headlines..." />
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
            {filtered.length} articles
          </span>
        </div>

        {/* Table header */}
        <div className="panel">
          <div style={{
            display: 'grid',
            gridTemplateColumns: '55px 110px 1fr 100px 40px',
            padding: '6px 14px',
            borderBottom: '1px solid var(--border)',
            gap: 10,
          }}>
            {['TIME','SOURCE','HEADLINE','SENTIMENT',''].map((h,i) => (
              <span key={i} className="label" style={{ textAlign: i>=3?'right':'left' }}>{h}</span>
            ))}
          </div>

          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>Loading news feed...</div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>No articles match your filters</div>
          ) : (
            <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 280px)' }}>
              {filtered.map((a, i) => (
                <a key={i} href={a.link} target="_blank" rel="noopener noreferrer"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '55px 110px 1fr 100px 40px',
                    padding: '8px 14px', gap: 10,
                    borderBottom: '1px solid var(--border-subtle)',
                    alignItems: 'center',
                    transition: 'background 100ms',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}
                >
                  <span className="mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    {(a.published || '').slice(0, 5)}
                  </span>
                  <span className="badge badge-muted" style={{ overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 105 }}>
                    {a.source}
                  </span>
                  <span style={{ fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.title}
                  </span>
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <SentimentBadge label={a.sentiment || 'Neutral'} />
                  </div>
                  <span style={{ color: 'var(--text-muted)', textAlign: 'center', fontSize: '13px' }}>↗</span>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NewsPage;
