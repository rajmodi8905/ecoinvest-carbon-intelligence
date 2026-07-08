import React from 'react';
import { useParams, Link } from 'react-router-dom';
import * as api from '../services/api';
import StatCard from '../components/StatCard';
import SentimentBadge from '../components/SentimentBadge';
import AgentTracePanel from '../components/AgentTracePanel';
import SWOTMatrix from '../components/SWOTMatrix';
import ImpactTranslator from '../components/ImpactTranslator';
import ReactMarkdown from 'react-markdown';
import RealtimeChart from '../components/RealtimeChart';
import ImpactDashboard from '../components/ImpactDashboard';

const fmtPrice = v => v ? `$${parseFloat(v).toFixed(2)}` : '—';
const fmtChg   = v => { const n = parseFloat(v); return <span className={`mono ${n>=0?'pos':'neg'}`}>{n>=0?'+':''}{n.toFixed(2)}%</span>; };
const fmtNum   = (v, d=3) => v != null ? parseFloat(v).toFixed(d) : '—';

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

const ReportPage = () => {
  const { id } = useParams(); // id is ticker or project ID
  
  const [data, setData] = React.useState(null);
  const [news, setNews] = React.useState([]);
  const [themes, setThemes] = React.useState([]);
  const [projects, setProjects] = React.useState([]);
  
  const [isProject, setIsProject] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  
  const [activeTab, setActiveTab] = React.useState('Overview');
  const [reportHtml, setReportHtml] = React.useState(() => sessionStorage.getItem(`report_${id}`) || '');

  // Reset report if we navigate to a new ID that isn't cached
  React.useEffect(() => {
    setReportHtml(sessionStorage.getItem(`report_${id}`) || '');
  }, [id]);

  React.useEffect(() => {
    const unsub = api.onDataUpdate('finance', (updates) => {
      const list = Array.isArray(updates) ? updates : updates?.data || [];
      const match = list.find(c => c.ticker === id);
      if (match) {
        setData(prev => prev ? { ...prev, ...match } : match);
      }
    });
    return () => {
      if (unsub) unsub();
    };
  }, [id]);

  React.useEffect(() => {
    // 1. Try to fetch as company
    api.getCompanyById(id).then(res => {
      if (res.success && res.data) {
        setIsProject(false);
        const comp = res.data;
        
        // Enrich with analytics data
        fetch('http://localhost:5001/api/analytics/top-movers')
          .then(r => r.json())
          .then(mv => {
            const enriched = mv.companies?.find(c => c.ticker === comp.ticker);
            setData(enriched ? { ...comp, ...enriched } : comp);
          });
          
        // Fetch news for company (fallback to industry if empty)
        api.fastSearch(comp.company_name || comp.ticker).then(fs => {
          if (fs.data?.news && fs.data.news.length > 0) {
            setNews(fs.data.news);
          } else if (comp.industry) {
            // Fallback to industry news
            fetch(`http://localhost:5001/api/news?limit=10`).then(r => r.json()).then(indNews => {
              // Optionally filter by industry keyword if backend doesn't support it, but for now just show top news
              setNews(indNews.data || []);
            }).catch(() => {});
          }
          if (fs.data?.projects) setProjects(fs.data.projects);
        });
        
        // Fetch themes
        fetch('http://localhost:5001/api/analytics/macro-themes')
          .then(r => r.json())
          .then(th => setThemes(th.themes?.slice(0,3).map(t=>t.theme) || []));
          
        setLoading(false);
      } else {
        // 2. Try as project
        api.getProjectById(id).then(pres => {
          if (pres.success) {
            setIsProject(true);
            setData(pres.data);
            
            // fetch news
            api.fastSearch(pres.data.name).then(fs => {
              if (fs.data?.news) setNews(fs.data.news);
            });
            setLoading(false);
          } else {
            setLoading(false);
          }
        });
      }
    });
  }, [id]);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading entity data...</div>;
  if (!data) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--red)' }}>Entity not found</div>;

  const title = isProject ? data.name : data.company_name;
  const subtitle = isProject ? `Project ID: ${data.id} | ${data.category}` : `Ticker: ${data.ticker} | ${data.industry}`;

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div className="page-header" style={{ paddingBottom: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Link to={isProject ? "/projects" : "/companies"} style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            ← {isProject ? 'Carbon Projects' : 'Companies'}
          </Link>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>/</span>
          <span style={{ fontSize: '11px', color: 'var(--green)' }}>{id}</span>
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <h1 style={{ fontSize: 24 }}>{title}</h1>
            <p style={{ marginTop: 4 }}>{subtitle}</p>
          </div>
          {isProject ? (
            <div style={{ textAlign: 'right' }}>
              <div className="mono pos" style={{ fontSize: 24, fontWeight: 600 }}>${data.price || 0}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>SPOT $/T</div>
            </div>
          ) : (
            <div style={{ textAlign: 'right' }}>
              <div className="mono" style={{ fontSize: 24, fontWeight: 600 }}>${data.price || data.stock_price || 0}</div>
              <div style={{ fontSize: 12, marginTop: 2 }}>{fmtChg(data.change_percent)}</div>
            </div>
          )}
        </div>
        
        {/* Tabs */}
        <div className="tab-bar">
          <div className={`tab-item ${activeTab === 'Overview' ? 'active' : ''}`} onClick={() => setActiveTab('Overview')}>Overview</div>
          <div className={`tab-item ${activeTab === 'AI Analysis' ? 'active' : ''}`} onClick={() => setActiveTab('AI Analysis')}>AI Analysis</div>
          <div className={`tab-item ${activeTab === 'News' ? 'active' : ''}`} onClick={() => setActiveTab('News')}>News</div>
        </div>
      </div>

      <div className="page-body" style={{ flex: 1 }}>
        {activeTab === 'Overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 16 }}>
            {/* Left Col */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {isProject ? (
                <div className="panel">
                  <div className="panel-header"><h3>Project Details</h3></div>
                  <div style={{ padding: '0 14px' }}>
                    <SignalRow label="Category" value={data.category || 'N/A'} />
                    <SignalRow label="Country" value={data.country || 'N/A'} />
                    <SignalRow label="Vintage" value={data.vintage || 'N/A'} />
                    <SignalRow label="Methodology" value={data.methodology || 'N/A'} />
                    <SignalRow label="Supply" value={data.available_credits ? Number(data.available_credits).toLocaleString() : 0} />
                    <SignalRow label="Status" value={data.registry_status || 'N/A'} />
                  </div>
                </div>
              ) : (
                <div className="panel">
                  <div className="panel-header"><h3>Live Signals</h3></div>
                  <div style={{ padding: '0 14px' }}>
                    <SignalRow label="Impact Rating"    value={data.impact_rating ? `${fmtNum(data.impact_rating)}/100` : 'N/A'} color={data.impact_rating>80?'var(--green)':data.impact_rating>60?'var(--amber)':'var(--red)'} />
                    <SignalRow label="Policy Alignment" value={data.policy_alignment ? `${fmtNum(data.policy_alignment)}%` : 'N/A'} color={data.policy_alignment>80?'var(--green)':data.policy_alignment>50?'var(--amber)':'var(--red)'} />
                    <SignalRow label="Momentum"         value={data.momentum ? `${data.momentum>=0?'+':''}${fmtNum(data.momentum)}` : '0.00'} color={data.momentum>0?'var(--green)':data.momentum<0?'var(--red)':'var(--text-muted)'} />
                    <SignalRow label="Market Risk"      value={fmtNum(data.risk)} color={data.risk>0.4?'var(--red)':data.risk>0.2?'var(--amber)':'var(--green)'} />
                    <SignalRow label="Sentiment (24h)"  value={`${data.sentiment_24h>=0?'+':''}${fmtNum(data.sentiment_24h)}`} color={data.sentiment_24h>0?'var(--green)':data.sentiment_24h<0?'var(--red)':'var(--text-muted)'} />
                    <SignalRow label="News Volume"      value={data.news_24h || 0} />
                    <SignalRow label="ESG Rating"       value={data.esg_rating || 'N/A'} />
                  </div>
                </div>
              )}
              
              {/* AI Powered Summary Panel */}
              {isProject ? (
                <ImpactTranslator projectId={id} />
              ) : (
                <SWOTMatrix ticker={id} />
              )}
            </div>
            
            {/* Right Col */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {data.description && (
                <div className="panel" style={{ padding: '16px 20px', fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                  {data.description}
                </div>
              )}
              
              {isProject ? (
                <div style={{ flex: 1 }}>
                  <ImpactDashboard data={data} />
                </div>
              ) : (
                <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '16px 20px' }}>
                  <RealtimeChart currentPrice={data.price} symbol={id} />
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'AI Analysis' && (
          <div style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: 16, height: '100%' }}>
            {/* Left: Agent Trace */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 12 }}>
                Multi-Agent Supervisor Pipeline
              </div>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 16 }}>
                A planner agent orchestrates specialized sub-agents (NewsAgent, MarketAgent, WebAgent) to gather live signals, search the Web, and synthesize a real-time research report.
              </p>
              
              <AgentTracePanel 
                id={id}
                streamUrl={`http://localhost:5001/api/${isProject ? 'project' : 'company'}/${id}/report/stream`}
                onComplete={html => {
                  setReportHtml(html);
                  sessionStorage.setItem(`report_${id}`, html);
                }}
              />
            </div>
            
            {/* Right: Rendered Report */}
            <div className="panel" style={{ padding: '24px 32px', overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
              {reportHtml ? (
                <div style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.6 }}>
                  <ReactMarkdown className="report-content markdown-body">
                    {reportHtml}
                  </ReactMarkdown>
                </div>
              ) : (
                <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                  Run generation to view report...
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'News' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%' }}>
            <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div className="panel-header"><h3>News & Content ({news.length})</h3></div>
              <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
                {news.length === 0 && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>No content available</div>}
                {news.map((a, i) => (
                  <a key={i} href={a.link || a.url} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'block', padding: '16px 24px', borderBottom: '1px solid var(--border-subtle)', transition: 'background 120ms' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-hover)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}
                  >
                    <div style={{ fontSize: 14, color: 'var(--text-primary)', marginBottom: 8, fontWeight: 500 }}>{a.title}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.5 }}>
                      {a.summary}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                      <span className="badge badge-muted">{a.source || 'News'}</span>
                      <SentimentBadge label={a.sentiment || 'Neutral'} />
                      <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: 12 }}>
                        {new Date(a.date).toLocaleDateString()}
                      </span>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Dynamic CSS for rendered markdown/html in report */}
      <style>{`
        .report-content h1, .report-content h2, .report-content h3, .report-content h4 { color: var(--text-primary); font-size: 14px; margin: 24px 0 12px 0; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
        .report-content h1:first-child, .report-content h2:first-child, .report-content h3:first-child, .report-content h4:first-child { margin-top: 0; }
        .report-content p { margin-bottom: 16px; }
        .report-content ul { padding-left: 20px; margin-bottom: 16px; }
        .report-content li { margin-bottom: 6px; }
        .report-content strong { color: var(--text-primary); }
      `}</style>
    </div>
  );
};

export default ReportPage;
