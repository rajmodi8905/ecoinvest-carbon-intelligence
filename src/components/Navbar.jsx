import React from 'react';
import { Search, Sparkles } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { io } from 'socket.io-client';
import * as api from '../services/api';
import LiveDot from './LiveDot';

const TABS = [
  { label: 'Dashboard',       path: '/' },
  { label: 'Credit Index',    path: '/index' },
  { label: 'Carbon Projects', path: '/projects' },
  { label: 'Companies',       path: '/companies' },
  { label: 'Macro',           path: '/macro' },
  { label: 'News',            path: '/news' },
];

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = React.useState('');
  const [isSearching, setIsSearching] = React.useState(false);
  const [suggestions, setSuggestions] = React.useState([]);
  const [showSuggestions, setShowSuggestions] = React.useState(false);
  const [latency, setLatency] = React.useState(null);

  React.useEffect(() => {
    const socket = io('http://localhost:5001');
    
    // Listen to pathway updates if they arrive
    socket.on('latency_update', (data) => {
      if (data.latency_ms && data.latency_ms > 0) {
        setLatency(Math.round(data.latency_ms));
      }
    });

    // Also manually ping every 2 seconds for real-time network latency
    const interval = setInterval(() => {
      const start = performance.now();
      socket.emit('ping', () => {
        setLatency(Math.round(performance.now() - start));
      });
    }, 2000);

    return () => {
      clearInterval(interval);
      socket.disconnect();
    };
  }, []);

  // ── Search logic (preserved from original) ─────────────────────────
  const performRAGSearch = async (query) => {
    if (!query.trim()) { setSuggestions([]); return; }
    setIsSearching(true);
    try {
      const [companyResult, fastSearchResult] = await Promise.all([
        api.searchCompanies(query).catch(() => ({ data: [] })),
        api.fastSearch(query).catch(() => ({ data: { projects: [], news: [] } })),
      ]);
      const companies = Array.isArray(companyResult) ? companyResult : companyResult?.data || [];
      const fastData = fastSearchResult?.data || { projects: [], news: [] };
      const combined = [];
      const seenIds = new Set();

      for (const c of companies) {
        const id = c.ticker || c.id;
        if (!seenIds.has(id)) {
          seenIds.add(id);
          combined.push({ id, name: c.company_name || c.name, type: 'Company', description: c.industry || '', url: `/report/${id}` });
        }
        if (combined.length >= 2) break;
      }
      for (const p of fastData.projects || []) {
        if (!seenIds.has(p.id)) {
          seenIds.add(p.id);
          combined.push({ id: p.id, name: p.name, type: 'Project', description: p.category || '', url: `/report/${p.id}` });
        }
      }
      for (const n of fastData.news || []) {
        combined.push({ id: n.id, name: n.title, type: 'News', description: '', url: n.url, external: true });
      }
      setSuggestions(combined);
    } catch {
      setSuggestions([]);
    } finally {
      setIsSearching(false);
    }
  };

  React.useEffect(() => {
    const t = setTimeout(() => { if (searchQuery) performRAGSearch(searchQuery); }, 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim() && suggestions.length > 0) {
      selectSuggestion(suggestions[0]);
    }
  };

  const selectSuggestion = (s) => {
    if (s.external) window.open(s.url, '_blank');
    else navigate(s.url);
    setSearchQuery('');
    setShowSuggestions(false);
  };

  const isActive = (path) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

  return (
    <nav style={{
      height: 'var(--nav-h)',
      background: 'var(--bg-elevated)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 16px',
      position: 'sticky',
      top: 'var(--ticker-h)',
      zIndex: 100,
      gap: '16px',
    }}>
      {/* Logo */}
      <Link to="/" style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        flexShrink: 0,
      }}>
        <span style={{ color: 'var(--green)', fontSize: '14px' }}>⬡</span>
        <span style={{
          fontFamily: 'var(--mono)',
          fontSize: '13px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          letterSpacing: '0.02em',
        }}>
          Carbon<span style={{ color: 'var(--green)' }}>Intel</span>
        </span>
      </Link>

      {/* Tab links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0', flex: 1 }}>
        {TABS.map(tab => (
          <Link
            key={tab.path}
            to={tab.path}
            style={{
              padding: '0 12px',
              height: 'var(--nav-h)',
              display: 'flex',
              alignItems: 'center',
              fontSize: '12px',
              fontWeight: 500,
              color: isActive(tab.path) ? 'var(--green)' : 'var(--text-muted)',
              borderBottom: isActive(tab.path) ? '2px solid var(--green)' : '2px solid transparent',
              transition: 'color 120ms, border-color 120ms',
              whiteSpace: 'nowrap',
              letterSpacing: '0.02em',
            }}
            onMouseEnter={e => { if (!isActive(tab.path)) e.currentTarget.style.color = 'var(--text-secondary)'; }}
            onMouseLeave={e => { if (!isActive(tab.path)) e.currentTarget.style.color = 'var(--text-muted)'; }}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* Search */}
      <div style={{ position: 'relative', width: '220px', flexShrink: 0 }}>
        <form onSubmit={handleSearch}>
          <div className="terminal-search" style={{ padding: '4px 8px' }}>
            <Search size={12} />
            <input
              type="text"
              value={searchQuery}
              onChange={e => { setSearchQuery(e.target.value); setShowSuggestions(true); }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder="Search..."
              style={{ fontSize: '11px' }}
            />
            {isSearching && <Sparkles size={11} className="animate-spin" style={{ color: 'var(--green)', flexShrink: 0 }} />}
          </div>
        </form>

        {/* Suggestions dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            zIndex: 999,
            overflow: 'hidden',
          }}>
            {suggestions.map(s => (
              <button
                key={s.id}
                onMouseDown={() => selectSuggestion(s)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '7px 10px',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'block',
                  cursor: 'pointer',
                  background: 'none',
                  transition: 'background 100ms',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-hover)'}
                onMouseLeave={e => e.currentTarget.style.background = 'none'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-primary)', fontWeight: 500 }}>{s.name}</span>
                  <span className="badge badge-muted" style={{ fontSize: '9px' }}>{s.type}</span>
                </div>
                {s.description && (
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '1px' }}>{s.description}</div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: LIVE indicator */}
      <div style={{ flexShrink: 0 }}>
        <LiveDot ms={latency} />
      </div>
    </nav>
  );
};

export default Navbar;
