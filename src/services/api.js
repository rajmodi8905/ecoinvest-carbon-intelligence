// API Client for Carbon Intelligence Backend
// Handles both REST API and WebSocket connections
// Author: Daksh Desai

import io from "socket.io-client";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5001";
const WS_URL = import.meta.env.VITE_WS_URL || "http://localhost:5001";

// WebSocket client singleton
let socket = null;
let socketCallbacks = {};

// Initialize WebSocket connection
export const initWebSocket = () => {
  if (socket?.connected) return socket;

  socket = io(WS_URL, {
    transports: ["websocket", "polling"],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5,
  });

  socket.on("connect", () => {
    console.log("✅ Connected to Carbon Intelligence Backend WebSocket");
  });

  socket.on("disconnect", () => {
    console.log("❌ Disconnected from backend WebSocket");
  });

  socket.on("connection_response", (data) => {
    console.log("Backend:", data.message);
  });

  // Auto-receive data updates (broadcast every 10 seconds)
  socket.on("data_update", (data) => {
    console.log("📊 Received live data update:", data.timestamp);
    if (socketCallbacks.analytics) {
      socketCallbacks.analytics(data.analytics);
    }
  });

  // Analytics updates
  socket.on("analytics_update", (data) => {
    if (socketCallbacks.analytics) {
      socketCallbacks.analytics(data);
    }
  });

  // Projects updates
  socket.on("projects_update", (data) => {
    if (socketCallbacks.projects) {
      socketCallbacks.projects(data);
    }
  });

  // Finance updates
  socket.on("finance_update", (data) => {
    if (socketCallbacks.finance) {
      socketCallbacks.finance(data);
    }
  });

  // News updates
  socket.on("news_update", (data) => {
    if (socketCallbacks.news) {
      socketCallbacks.news(data);
    }
  });

  // Insights updates (Pathway Advanced Stream Analytics)
  socket.on("insights_update", (data) => {
    if (socketCallbacks.insights) {
      socketCallbacks.insights(data);
    }
  });

  // Frontend action listeners
  socket.on("change_theme", (data) => {
    console.log("🎨 Received change_theme event:", data);
    if (socketCallbacks.change_theme) {
      socketCallbacks.change_theme(data);
    } else {
      console.warn("⚠️ No callback registered for change_theme");
    }
  });

  socket.on("add_to_watchlist", (data) => {
    console.log("➕ Received add_to_watchlist event:", data);
    if (socketCallbacks.add_to_watchlist) {
      socketCallbacks.add_to_watchlist(data);
    } else {
      console.warn("⚠️ No callback registered for add_to_watchlist");
    }
  });

  socket.on("remove_from_watchlist", (data) => {
    console.log("➖ Received remove_from_watchlist event:", data);
    if (socketCallbacks.remove_from_watchlist) {
      socketCallbacks.remove_from_watchlist(data);
    } else {
      console.warn("⚠️ No callback registered for remove_from_watchlist");
    }
  });

  socket.on("navigate", (data) => {
    console.log("🧭 Received navigate event:", data);
    if (socketCallbacks.navigate) {
      socketCallbacks.navigate(data);
    } else {
      console.warn("⚠️ No callback registered for navigate");
    }
  });

  // Report generation progress events
  socket.on("report_progress", (data) => {
    console.log("📊 Report progress:", data);
    if (socketCallbacks.report_progress) {
      socketCallbacks.report_progress(data);
    }
  });

  return socket;
};

// Register callback for data updates
export const onDataUpdate = (type, callback) => {
  socketCallbacks[type] = callback;
};



// ============================================================================
// REST API FUNCTIONS
// ============================================================================

// Generic fetch wrapper with error handling
const apiFetch = async (endpoint, options = {}) => {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error fetching ${endpoint}:`, error);
    throw error;
  }
};



// ============================================================================
// PROJECTS API
// ============================================================================

export const getProjects = async (
  limit = 100,
  country = null,
  category = null
) => {
  let url = `/api/projects?limit=${limit}`;
  if (country) url += `&country=${country}`;
  if (category) url += `&category=${category}`;
  return apiFetch(url);
};

export const getProjectById = async (id) => {
  return apiFetch(`/api/project/${id}`);
};

export const getProjectReport = async (id, forceRefresh = false, onlyCached = false) => {
  return apiFetch(`/api/project/${id}/report?forceRefresh=${forceRefresh}&onlyCached=${onlyCached}`);
};

export const askProjectQuestion = async (id, query) => {
  return apiFetch(`/api/project/${id}/custom-query`, {
    method: "POST",
    body: JSON.stringify({ query }),
  });
};

export const searchProjects = async (query, limit = 50) => {
  return apiFetch("/api/projects/search", {
    method: "POST",
    body: JSON.stringify({ query, limit }),
  });
};

// ============================================================================
// FINANCE & ESG API
// ============================================================================

const getFinance = async (ticker = null) => {
  const url = ticker ? `/api/finance?ticker=${ticker}` : "/api/finance";
  return apiFetch(url);
};



// Alias for backward compatibility
export const getCompanies = async () => {
  const result = await getFinance();
  return result.data || [];
};

export const searchCompanies = async (query, limit = 10) => {
  const companies = await getCompanies();
  const normalizedQuery = query.trim().toLowerCase();

  if (!normalizedQuery) {
    return [];
  }

  return companies
    .filter((company) => {
      const searchableFields = [
        company.name,
        company.company_name,
        company.ticker,
        company.id,
        company.industry,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableFields.includes(normalizedQuery);
    })
    .slice(0, limit);
};

export const getCompanyById = async (ticker) => {
  const result = await apiFetch(`/api/company/${ticker}`);
  return result;
};

export const getCompanyInsights = async (ticker, forceRefresh = false, onlyCached = false) => {
  const result = await apiFetch(`/api/company/${ticker}/insights?forceRefresh=${forceRefresh}&onlyCached=${onlyCached}`);
  return result;
};

export const getFutureImpactAnalysis = async (ticker, forceRefresh = false, onlyCached = false) => {
  const result = await apiFetch(`/api/company/${ticker}/future-impact?forceRefresh=${forceRefresh}&onlyCached=${onlyCached}`);
  return result;
};

export const askCompanyQuestion = async (ticker, query) => {
  const result = await apiFetch(`/api/company/${ticker}/custom-query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
  });
  return result;
};

// ============================================================================
// NEWS API
// ============================================================================

export const getNews = async (limit = 350, source = null) => {
  let url = `/api/news?limit=${limit}`;
  if (source) url += `&source=${source}`;
  return apiFetch(url);
};



// ============================================================================
// ANALYTICS API
// ============================================================================

export const getAnalytics = async () => {
  return apiFetch("/api/analytics");
};



// ============================================================================
// LEGACY COMPATIBILITY (for existing frontend code)
// ============================================================================



// ============================================================================
// FRONTEND ACTIONS API
// ============================================================================

export const changeTheme = async () => {
  return apiFetch("/api/frontend/change_theme", {
    method: "POST",
  });
};

export const addToWatchlist = async (companyName, companySymbol) => {
  return apiFetch("/api/frontend/add_to_watchlist", {
    method: "POST",
    body: JSON.stringify({
      company_name: companyName,
      company_symbol: companySymbol,
    }),
  });
};

export const removeFromWatchlist = async (companyName) => {
  return apiFetch("/api/frontend/remove_from_watchlist", {
    method: "POST",
    body: JSON.stringify({ company_name: companyName }),
  });
};



// ============================================================================
// AI CHAT API
// ============================================================================

export const sendChatMessage = async (message, sessionId = null) => {
  const payload = { message };
  if (sessionId) {
    payload.session_id = sessionId;
  }
  // Chat API can return 429 when Gemini quota is hit; avoid throwing so UI can show the message.
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  return { status: response.status, ok: response.ok, ...data };
};

// ============================================================================
// EXPORT DEFAULT OBJECT
// ============================================================================

export default {
  // WebSocket
  initWebSocket,
  onDataUpdate,



  // Projects
  getProjects,
  getProjectById,
  getProjectReport,
  askProjectQuestion,
  searchProjects,

  // Finance & ESG
  getFinance,
  getCompanies,
  searchCompanies,
  getCompanyById,
  getCompanyInsights,
  getFutureImpactAnalysis,
  askCompanyQuestion,

  // News
  getNews,

  // Analytics
  getAnalytics,


  // Frontend Actions
  changeTheme,
  addToWatchlist,
  removeFromWatchlist,

  // AI Chat
  sendChatMessage,
};
