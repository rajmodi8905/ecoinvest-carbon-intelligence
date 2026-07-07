import React from 'react';
import { Leaf, Search, Sparkles, Sun, Moon, Zap } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { ThemeContext } from '../context/ThemeContext';
import api from '../services/api';
import { io } from 'socket.io-client';

const Navbar = () => {
  const { theme, toggleTheme } = React.useContext(ThemeContext);
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = React.useState('');
  const [isSearching, setIsSearching] = React.useState(false);
  const [suggestions, setSuggestions] = React.useState([]);
  const [showSuggestions, setShowSuggestions] = React.useState(false);
  const [liveLatency, setLiveLatency] = React.useState(321); // Default to last benchmarked 321ms

  React.useEffect(() => {
    // Setup socket connection for real-time latency
    const socket = io('http://localhost:5001');
    socket.on('latency_update', (data) => {
      if (data.latency_ms && data.latency_ms > 0) {
        setLiveLatency(data.latency_ms);
      }
    });

    return () => socket.disconnect();
  }, []);

  // Real-time search using backend API
  const performRAGSearch = async (query) => {
    if (!query.trim()) {
      setSuggestions([]);
      return;
    }

    setIsSearching(true);
    
    try {
      // Run both standard company search and our new Fast RAG Search in parallel!
      const [companyResult, fastSearchResult] = await Promise.all([
        api.searchCompanies(query).catch(() => ({ data: [] })),
        api.fastSearch(query).catch(() => ({ data: { projects: [], news: [] } }))
      ]);
      
      const companies = Array.isArray(companyResult) ? companyResult : companyResult?.data || [];
      const fastData = fastSearchResult?.data || { projects: [], news: [] };
      
      const combinedSuggestions = [];
      
      // 1. Add top 2 Companies
      const seenIds = new Set();
      for (const c of companies) {
        const id = c.ticker || c.id;
        if (!seenIds.has(id)) {
          seenIds.add(id);
          combinedSuggestions.push({
            id: id,
            name: c.company_name || c.name,
            type: 'Company',
            description: c.industry || c.description || '',
            url: `/report/${id}`
          });
        }
        if (combinedSuggestions.length >= 2) break;
      }
      
      // 2. Add top 3 Projects from Fast RAG
      for (const p of fastData.projects || []) {
        if (!seenIds.has(p.id)) {
          seenIds.add(p.id);
          combinedSuggestions.push({
            id: p.id,
            name: p.name,
            type: 'Project',
            description: `Fast RAG Match: ${p.category || ''}`,
            url: `/report/${p.id}`
          });
        }
      }
      
      // 3. Add top 2 News from Fast RAG
      for (const n of fastData.news || []) {
        combinedSuggestions.push({
          id: n.id,
          name: n.title,
          type: 'News',
          description: `Fast RAG News Article`,
          url: n.url,
          external: true
        });
      }
      
      setSuggestions(combinedSuggestions);
    } catch (error) {
      console.error('Search error:', error);
      setSuggestions([]);
    } finally {
      setIsSearching(false);
    }
  };

  React.useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery) {
        performRAGSearch(searchQuery);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim() && suggestions.length > 0) {
      const first = suggestions[0];
      if (first.external) {
        window.open(first.url, '_blank');
      } else {
        navigate(first.url);
      }
      setSearchQuery('');
      setShowSuggestions(false);
    }
  };

  const selectSuggestion = (suggestion) => {
    if (suggestion.external) {
      window.open(suggestion.url, '_blank');
    } else {
      navigate(suggestion.url);
    }
    setSearchQuery('');
    setShowSuggestions(false);
  };

  return (
    <nav className={`${theme === 'dark' ? 'bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-green-500/30' : 'bg-white border-gray-200'} backdrop-blur-xl bg-opacity-90 shadow-lg sticky top-0 z-50 border-b animate-fadeIn`}>
      <div className={`absolute inset-0 bg-gradient-to-r from-green-500/5 via-emerald-500/5 to-green-500/5 ${theme === 'dark' ? 'opacity-50' : 'opacity-20'}`}></div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div className="flex justify-between items-center h-16 gap-8">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 hover:scale-105 transition-all duration-300 group relative">
            <div className="relative">
              <Leaf className={`w-8 h-8 ${theme === 'dark' ? 'text-green-400' : 'text-green-600'} group-hover:rotate-12 transition-all duration-500`} />
              <div className={`absolute inset-0 ${theme === 'dark' ? 'bg-green-400' : 'bg-green-600'} blur-2xl opacity-40 group-hover:opacity-70 transition-opacity`}></div>
            </div>
            <span className={`text-2xl font-bold ${theme === 'dark' ? 'bg-gradient-to-r from-green-400 via-green-300 to-emerald-400 bg-clip-text text-transparent' : 'text-green-700'} drop-shadow-lg gradient-animate`}>EcoInvest</span>
          </Link>

          {/* Unified RAG Search Bar */}
          <div className="flex-1 max-w-2xl relative group">
            <form onSubmit={handleSearch} className="relative">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-xl blur-md opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setShowSuggestions(true);
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                  placeholder="Search companies, reports, ESG data..."
                  className={`relative w-full px-6 py-3 pl-12 pr-12 ${theme === 'dark' ? 'text-slate-200 bg-slate-800/60 placeholder-slate-400' : 'text-slate-800 bg-white/60 placeholder-slate-500'} backdrop-blur-xl border border-green-500/40 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-green-400 ${theme === 'dark' ? 'focus:bg-slate-800/80' : 'focus:bg-white/80'} shadow-xl transition-all duration-300 hover:border-green-400/60`}
                />
                <Search className="absolute left-4 top-3.5 w-5 h-5 text-green-400 group-hover:scale-110 transition-transform duration-300" />
                {isSearching && (
                  <Sparkles className="absolute right-4 top-3.5 w-5 h-5 text-green-400 animate-spin drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
                )}
              </div>

              {/* Search Suggestions Dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <div className={`absolute top-full mt-2 w-full ${theme === 'dark' ? 'bg-slate-900/95' : 'bg-white'} backdrop-blur-xl border ${theme === 'dark' ? 'border-slate-700' : 'border-gray-200'} rounded-lg shadow-2xl overflow-hidden animate-scaleIn`}>
                  <div className="max-h-64 overflow-y-auto">
                    {suggestions.map((item, idx) => (
                      <button
                        key={item.id}
                        onClick={() => selectSuggestion(item)}
                        className={`w-full text-left px-4 py-2.5 ${theme === 'dark' ? 'hover:bg-slate-800 border-slate-700/50' : 'hover:bg-gray-50 border-gray-200'} transition-colors duration-200 border-b last:border-b-0 group cursor-pointer`}
                      >
                        <div className="flex items-start justify-between pointer-events-none">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className={`font-medium text-sm ${theme === 'dark' ? 'text-slate-200 group-hover:text-green-400' : 'text-slate-800 group-hover:text-green-600'} transition-colors`}>{item.name}</span>
                              <span className={`text-xs px-1.5 py-0.5 ${theme === 'dark' ? 'bg-green-500/20 text-green-400' : 'bg-green-100 text-green-700'} rounded`}>{item.id}</span>
                            </div>
                            {item.description && (
                              <p className={`text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'} mt-0.5`}>{item.description}</p>
                            )}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </form>
          </div>

          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2 bg-green-500/10 text-green-500 px-3 py-1.5 rounded-full text-sm font-medium border border-green-500/20 shadow-[0_0_10px_rgba(34,197,94,0.2)] animate-pulse">
              <Zap className="h-4 w-4" />
              <span>Live Data: {(liveLatency / 1000).toFixed(2)}s</span>
            </div>
            
            <Link
              to="/"
              className={`${theme === 'dark' ? 'text-slate-300 hover:text-green-400' : 'text-slate-700 hover:text-green-600'} font-semibold transition-all duration-300 relative group px-2 py-1`}
            >
              <span className="relative z-10">Dashboard</span>
              <span className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-green-400 via-emerald-400 to-green-400 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left rounded-full"></span>
              <span className="absolute inset-0 bg-green-500/10 rounded-lg scale-0 group-hover:scale-100 transition-transform duration-300 blur-sm"></span>
            </Link>
            <Link
              to="/projects"
              className={`${theme === 'dark' ? 'text-slate-300 hover:text-green-400' : 'text-slate-700 hover:text-green-600'} font-semibold transition-all duration-300 relative group px-2 py-1`}
            >
              <span className="relative z-10">Projects</span>
              <span className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-green-400 via-emerald-400 to-green-400 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left rounded-full"></span>
              <span className="absolute inset-0 bg-green-500/10 rounded-lg scale-0 group-hover:scale-100 transition-transform duration-300 blur-sm"></span>
            </Link>
            
            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className={`relative p-2 rounded-lg ${theme === 'dark' ? 'bg-slate-800/50 border-green-500/30' : 'bg-gray-100 border-gray-300'} border hover:border-green-500 transition-all duration-300 hover:scale-110 group`}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-green-400 group-hover:rotate-180 transition-transform duration-500" />
              ) : (
                <Moon className="w-5 h-5 text-green-600 group-hover:-rotate-12 transition-transform duration-500" />
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;

