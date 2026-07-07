import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import TickerTape from './components/TickerTape';
import AIChat from './components/AIChat';
import Dashboard from './pages/Dashboard';
import ReportPage from './pages/ReportPage';
import ProjectsPage from './pages/ProjectsPage';
import CreditIndexPage from './pages/CreditIndexPage';
import CompaniesPage from './pages/CompaniesPage';
import MacroPage from './pages/MacroPage';
import MacroDetailPage from './pages/MacroDetailPage';
import NewsPage from './pages/NewsPage';
import * as api from './services/api';
import './index.css';

function AppContent() {
  const navigate = useNavigate();
  const [companies, setCompanies] = React.useState([]);

  React.useEffect(() => {
    // Init WebSocket once
    api.initWebSocket();

    // Populate ticker tape on load
    api.getCompanies().then(data => {
      if (Array.isArray(data)) setCompanies(data);
    }).catch(() => {});

    // Live finance updates → keep ticker tape fresh
    api.onDataUpdate('finance', (data) => {
      const list = Array.isArray(data) ? data : data?.data || [];
      if (list.length > 0) setCompanies(list);
    });

    // Navigation commands from AI bot
    api.onDataUpdate('navigate', (data) => {
      if (data.action === 'projects')       navigate('/projects');
      else if (data.action === 'companies') navigate('/companies');
      else if (data.action === 'macro')     navigate('/macro');
      else if (data.action === 'news')      navigate('/news');
      else if (data.action === 'index')     navigate('/index');
      else if (data.action === 'project')   navigate(`/report/${data.project_id}`);
      else if (data.action === 'company')   navigate(`/report/${data.ticker || data.company_name}`);
    });
  }, [navigate]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      {/* Scrolling equity tape — topmost element */}
      <TickerTape companies={companies} />

      {/* Bloomberg nav bar */}
      <Navbar />

      {/* Page content */}
      <main style={{ flex: 1, overflowY: 'auto' }}>
        <Routes>
          <Route path="/"              element={<Dashboard />} />
          <Route path="/index"         element={<CreditIndexPage />} />
          <Route path="/projects"      element={<ProjectsPage />} />
          <Route path="/companies"     element={<CompaniesPage />} />
          <Route path="/macro"         element={<MacroPage />} />
          <Route path="/macro/:theme"  element={<MacroDetailPage />} />
          <Route path="/news"          element={<NewsPage />} />
          <Route path="/report/:id"    element={<ReportPage />} />
        </Routes>
      </main>

      {/* Floating AI chat — always visible */}
      <AIChat />
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
