import React from 'react';
import { Link, useParams } from 'react-router-dom';
import StatCard from '../components/StatCard';
import SentimentBadge from '../components/SentimentBadge';

const fmtNum = (v, d=3) => v != null ? parseFloat(v).toFixed(d) : '—';

const SignalRow = ({ label, value, color }) => (
  <div style={{
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '7px 0',
    borderBottom: '1px solid var(--border-subtle)',
  }}>
    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{label}</span>
    <span className="mono" style={{ fontSize: '12px', color: color || 'var(--text-primary)' }}>{value}</span>
  </div>
);

const MacroDetailPage = () => {
  const { theme } = useParams();
  const decoded = decodeURIComponent(theme);

  const [themeData, setThemeData] = React.useState(null);
  const [news, setNews] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    // Fetch macro themes and filter for this one
    Promise.all([
      fetch('http://localhost:5001/api/analytics/macro-themes').then(r => r.json()),
      fetch('http://localhost:5001/api/news?limit=500').then(r => r.json()),
    ]).then(([macroRes, newsRes]) => {
      const found = (macroRes.themes || []).find(t => t.theme === decoded);
      setThemeData(found || null);

      // Filter news by keyword matching (client-side)
      const keywords = decoded.toLowerCase().split(/[\s&]+/).filter(w => w.length > 3);
      const allNews = newsRes.data || [];
      const matched = allNews.filter(a => {
        const text = ((a.title || '') + ' ' + (a.summary || '')).toLowerCase();
        return keywords.some(kw => text.includes(kw));
      });
      setNews(matched.slice(0, 200));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [decoded]);

  const sentColor = v => {
    const n = parseFloat(v);
    return n > 0 ? 'var(--green)' : n < 0 ? 'var(--red)' : 'var(--text-muted)';
  };

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100%' }}>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Link to="/macro" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>← Macro Themes</Link>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>/</span>
          <span style={{ fontSize: '11px', color: 'var(--green)' }}>{decoded}</span>
        </div>
        <h1>{decoded}</h1>
        <p>Climate / policy narrative — live coverage &amp; sentiment</p>
      </div>

      {loading ? (
        <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>Loading...</div>
      ) : (
        <div className="page-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* KPI cards */}
          <div className="stat-grid">
            <StatCard label="24H Articles"     value={themeData?.articles_24h ?? '—'}   sublabel={`${themeData?.articles_1h ?? 0} in last hour`} />
            <StatCard label="Impact Score"     value={themeData?.impact != null ? fmtNum(themeData.impact, 1) : '—'} sublabel="relevance metric" valueColor={parseFloat(themeData?.impact??0)>80?'var(--green)':'var(--text-primary)'} />
            <StatCard label="Sentiment"        value={themeData?.sentiment != null ? `${parseFloat(themeData.sentiment)>=0?'+':''}${fmtNum(themeData.sentiment)}` : '—'}
              sublabel="rolling mean"
              valueColor={sentColor(themeData?.sentiment ?? 0)}
            />
            <StatCard label="Momentum"         value={themeData?.momentum != null ? fmtNum(themeData.momentum) : '—'}
              sublabel="trend strength"
              valueColor={parseFloat(themeData?.momentum??0)>0?'var(--green)':parseFloat(themeData?.momentum??0)<0?'var(--red)':'var(--text-muted)'}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 12 }}>
            {/* Live Signals */}
            <div className="panel">
              <div className="panel-header">
                <h3>Live Signals <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 400 }}>— computed by analytics_service</span></h3>
              </div>
              <div style={{ padding: '0 14px' }}>
                <SignalRow label="Theme"                value={decoded} />
                <SignalRow label="Sentiment (rolling)"  value={`${parseFloat(themeData?.sentiment??0)>=0?'+':''}${fmtNum(themeData?.sentiment)}`} color={sentColor(themeData?.sentiment??0)} />
                <SignalRow label="Momentum"             value={themeData?.momentum != null ? fmtNum(themeData.momentum) : '—'} color={parseFloat(themeData?.momentum??0)>0?'var(--green)':parseFloat(themeData?.momentum??0)<0?'var(--red)':'var(--text-muted)'} />
                <SignalRow label="Impact Rating"        value={themeData?.impact != null ? fmtNum(themeData.impact, 1) : '—'} color={parseFloat(themeData?.impact??0)>80?'var(--green)':'var(--text-primary)'} />
                <SignalRow label="Articles — last hour" value={themeData?.articles_1h ?? '—'} />
                <SignalRow label="Articles — last 24h"  value={themeData?.articles_24h ?? '—'} />
                <div style={{ padding: '8px 0 4px' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: 4 }}>Latest headline</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    {themeData?.latest_headline || '—'}
                  </div>
                </div>
              </div>
            </div>

            {/* News feed */}
            <div className="panel">
              <div className="panel-header">
                <h3>News — last 24h ({news.length})</h3>
              </div>
              <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 380px)' }}>
                {news.length === 0 && (
                  <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                    No matching news articles found
                  </div>
                )}
                {news.map((a, i) => (
                  <a key={i} href={a.link} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'block', padding: '9px 14px', borderBottom: '1px solid var(--border-subtle)', transition: 'background 100ms' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-hover)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}
                  >
                    <div style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.4, marginBottom: 4 }}>{a.title}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                      <span className="mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                        {(a.published || '').slice(0, 5)}
                      </span>
                      <span className="badge badge-muted">{a.source}</span>
                      <span className="badge badge-blue">{decoded}</span>
                      <SentimentBadge label={a.sentiment || 'Neutral'} />
                    </div>
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MacroDetailPage;
