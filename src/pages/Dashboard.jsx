import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, ExternalLink, Trash2, X, Sparkles } from "lucide-react";
import DashboardChatSidebar from "../components/DashboardChatSidebar";
import { ThemeContext } from "../context/ThemeContext";
import Fuse from "fuse.js";
import api from "../services/api";

const Dashboard = () => {
  const { theme } = React.useContext(ThemeContext);
  const navigate = useNavigate();

  // State for data from backend
  const [allCompanies, setAllCompanies] = React.useState([]);
  const [news, setNews] = React.useState([]);
  const [analytics, setAnalytics] = React.useState(null);
  const [lastUpdate, setLastUpdate] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  
  // Progress tracking state
  const [loadingSteps, setLoadingSteps] = React.useState([]);
  const [currentLoadingStep, setCurrentLoadingStep] = React.useState(null);

  // Initialize watchlist from localStorage (moved here before useEffect)
  const [watchlist, setWatchlist] = React.useState(() => {
    const saved = localStorage.getItem("watchlist");
    return saved ? JSON.parse(saved) : [];
  });

  // Persist watchlist to localStorage whenever it changes
  React.useEffect(() => {
    localStorage.setItem("watchlist", JSON.stringify(watchlist));
  }, [watchlist]);

  // Fetch data from backend on mount
  React.useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setLoadingSteps([]);
        
        // Step 1: Fetching companies
        setCurrentLoadingStep('Loading company data...');
        setLoadingSteps([{ step: 1, message: 'Fetching companies...', timestamp: Date.now() }]);
        const companiesPromise = api.getCompanies();
        
        // Step 2: Fetching news
        setCurrentLoadingStep('Loading latest news...');
        setLoadingSteps(prev => [...prev, { step: 2, message: 'Fetching news articles...', timestamp: Date.now() }]);
        const newsPromise = api.getNews(350);
        
        // Step 3: Fetching analytics
        setCurrentLoadingStep('Loading analytics...');
        setLoadingSteps(prev => [...prev, { step: 3, message: 'Analyzing market data...', timestamp: Date.now() }]);
        const analyticsPromise = api.getAnalytics();
        
        const [companiesData, newsData, analyticsData] = await Promise.all([
          companiesPromise,
          newsPromise,
          analyticsPromise,
        ]);
        setAllCompanies(companiesData || []);
        console.log("✅ Companies loaded:", companiesData?.length, "companies");
        console.log("📊 Sample company data:", companiesData?.[0]);
        // Ensure newsData is always an array - API returns {count, data}
        const newsArray = Array.isArray(newsData)
          ? newsData
          : newsData?.data || [];
        // Sort news by date (latest first)
        const sortedNews = newsArray.sort((a, b) => {
          const dateA = new Date(a.date || a.published || 0);
          const dateB = new Date(b.date || b.published || 0);
          return dateB - dateA; // Descending order (latest first)
        });
        setNews(sortedNews);
        console.log("✅ News loaded:", sortedNews.length, "articles");
        console.log("📊 Analytics loaded:", analyticsData);
        console.log("📊 Projects metrics:", analyticsData?.projects);
        setAnalytics(analyticsData);
        setError(null);
        
        // Final step
        setLoadingSteps(prev => [...prev, { step: 4, message: 'Dashboard ready!', timestamp: Date.now() }]);
        setCurrentLoadingStep(null);
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to load data. Please check if backend is running.");
        // Fallback to empty arrays
        setAllCompanies([]);
        setNews([]);
        setCurrentLoadingStep(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Set up WebSocket for real-time updates
    try {
      api.initWebSocket();

      // Listen for analytics updates (broadcast every 10 seconds)
      api.onDataUpdate("analytics", (data) => {
        console.log("📊 Analytics updated via WebSocket:", data);
        console.log("📊 Projects data:", data?.projects);
        setAnalytics(data);
        setLastUpdate(new Date().toLocaleTimeString());
      });

      api.onDataUpdate("finance", (data) => {
        console.log("💰 Finance data updated via WebSocket");
        // WebSocket returns {success, data} structure
        const companies = Array.isArray(data) ? data : data?.data || [];
        console.log("📊 Sample WebSocket data:", companies?.[0]);
        setAllCompanies(companies);
      });

      api.onDataUpdate("news", (data) => {
        console.log("📰 News updated via WebSocket");
        // API returns {count, data} structure
        const newsArray = Array.isArray(data) ? data : data?.data || [];
        // Sort news by date (latest first)
        const sortedNews = newsArray.sort((a, b) => {
          const dateA = new Date(a.date || a.published || 0);
          const dateB = new Date(b.date || b.published || 0);
          return dateB - dateA; // Descending order (latest first)
        });
        setNews(sortedNews);
        console.log("✅ News updated:", sortedNews.length, "articles");
      });

      // Listen for watchlist commands (from other tabs or AI bot)
      let addWatchlistTimeout = null;
      api.onDataUpdate("add_to_watchlist", (data) => {
        console.log("➕ ADD TO WATCHLIST EVENT RECEIVED:", data);

        // Debounce to prevent duplicate events
        if (addWatchlistTimeout) {
          console.log("⏱️ Ignoring duplicate add to watchlist event");
          return;
        }

        const { company_name, company_symbol } = data;

        // First try to find in allCompanies list
        setAllCompanies((currentCompanies) => {
          const company = currentCompanies.find(
            (c) =>
              c.name?.toLowerCase() === company_name?.toLowerCase() ||
              c.company_name?.toLowerCase() === company_name?.toLowerCase() ||
              c.id?.toLowerCase() === company_symbol?.toLowerCase() ||
              c.ticker?.toLowerCase() === company_symbol?.toLowerCase()
          );

          if (company) {
            // Check if already in watchlist and add if not
            setWatchlist((prev) => {
              const alreadyInWatchlist = prev.some((c) => c.id === company.id);
              if (!alreadyInWatchlist) {
                console.log(
                  "✅ Syncing watchlist: added",
                  company.name || company.company_name
                );
                return [...prev, company];
              } else {
                console.log("ℹ️ Company already in watchlist (no sync needed)");
                return prev;
              }
            });
          } else {
            console.log(
              "⚠️ Company not found in allCompanies, trying to fetch..."
            );
            // If company not found in local list, fetch it from backend
            api
              .getCompanyById(company_symbol)
              .then((result) => {
                if (result.success && result.data) {
                  const fetchedCompany = result.data;
                  setWatchlist((prev) => {
                    const alreadyInWatchlist = prev.some(
                      (c) => c.id === fetchedCompany.ticker
                    );
                    if (!alreadyInWatchlist) {
                      console.log(
                        "✅ Syncing watchlist: added (fetched)",
                        fetchedCompany.company_name
                      );
                      return [
                        ...prev,
                        {
                          id: fetchedCompany.ticker,
                          name: fetchedCompany.company_name,
                          company_name: fetchedCompany.company_name,
                          ticker: fetchedCompany.ticker,
                          industry: fetchedCompany.industry,
                          esg_score: fetchedCompany.esg_score,
                        },
                      ];
                    }
                    return prev;
                  });
                }
              })
              .catch((err) => {
                console.error("❌ Error fetching company:", err);
              });
          }

          return currentCompanies; // Return unchanged
        });

        // Set timeout to allow next add after 500ms
        addWatchlistTimeout = setTimeout(() => {
          addWatchlistTimeout = null;
        }, 500);
      });

      let removeWatchlistTimeout = null;
      api.onDataUpdate("remove_from_watchlist", (data) => {
        console.log("➖ REMOVE FROM WATCHLIST EVENT RECEIVED:", data);

        // Debounce to prevent duplicate events
        if (removeWatchlistTimeout) {
          console.log("⏱️ Ignoring duplicate remove from watchlist event");
          return;
        }

        const { company_name } = data;

        // Find and remove the company (sync from other tabs/AI)
        setWatchlist((prev) => {
          const filtered = prev.filter(
            (c) =>
              c.name?.toLowerCase() !== company_name?.toLowerCase() &&
              c.company_name?.toLowerCase() !== company_name?.toLowerCase() &&
              c.id?.toLowerCase() !== company_name?.toLowerCase()
          );
          if (filtered.length < prev.length) {
            console.log("✅ Syncing watchlist: removed", company_name);
          } else {
            console.log("ℹ️ Company not in watchlist (no sync needed)");
          }
          return filtered;
        });

        // Set timeout to allow next remove after 500ms
        removeWatchlistTimeout = setTimeout(() => {
          removeWatchlistTimeout = null;
        }, 500);
      });

      // Listen for watchlist requests from backend (AI chatbot)
      api.onDataUpdate("request_watchlist", () => {
        console.log("📋 Backend requested watchlist");
        // Send current watchlist to backend
        const socket = api.initWebSocket();
        socket.emit("watchlist_update", { watchlist });
      });
    } catch (err) {
      console.warn("WebSocket not available:", err);
    }
  }, []);

  // Send watchlist updates to backend whenever it changes
  React.useEffect(() => {
    try {
      const socket = api.initWebSocket();
      if (socket && socket.connected) {
        socket.emit("watchlist_update", { watchlist });
        console.log("📋 Sent watchlist update to backend:", watchlist.length, "companies");
      }
    } catch (err) {
      console.warn("Could not send watchlist update:", err);
    }
  }, [watchlist]);

  // Set default companies when data loads and watchlist is empty
  React.useEffect(() => {
    if (allCompanies.length > 0 && watchlist.length === 0) {
      // Helper to convert ESG rating to numeric for sorting
      const esgToNumeric = (rating) => {
        const ratingMap = {
          AAA: 100,
          AA: 90,
          A: 80,
          BBB: 70,
          BB: 60,
          B: 50,
          CCC: 40,
        };
        return ratingMap[rating] || 0;
      };

      // Get top 3 companies by ESG rating
      const topCompanies = [...allCompanies]
        .sort((a, b) => esgToNumeric(b.esg_rating) - esgToNumeric(a.esg_rating))
        .slice(0, 3);

      if (topCompanies.length > 0) {
        setWatchlist(topCompanies);
        console.log(
          "📊 Default watchlist set with top ESG companies:",
          topCompanies.map((c) => c.name || c.company_name)
        );
      }
    }
  }, [allCompanies]);

  const [searchQuery, setSearchQuery] = React.useState("");
  const [suggestions, setSuggestions] = React.useState([]);
  const [showSuggestions, setShowSuggestions] = React.useState(false);

  // Add Company Modal State
  const [isAddModalOpen, setIsAddModalOpen] = React.useState(false);
  const [addSearchQuery, setAddSearchQuery] = React.useState("");
  const [addSuggestions, setAddSuggestions] = React.useState([]);

  // Initialize Fuse for fuzzy search (for Add Company modal)
  const fuse = React.useMemo(() => {
    return new Fuse(allCompanies, {
      keys: ["name", "id", "industry"],
      threshold: 0.4,
      distance: 100,
    });
  }, [allCompanies]);

  // Add Modal Search Effect
  React.useEffect(() => {
    if (addSearchQuery.trim() === "") {
      setAddSuggestions([]);
      return;
    }
    const results = fuse.search(addSearchQuery);

    // Remove duplicates by using unique IDs
    const uniqueCompanies = [];
    const seenIds = new Set();

    for (const result of results) {
      const company = result.item;
      const id = company.ticker || company.id;
      if (!seenIds.has(id)) {
        seenIds.add(id);
        uniqueCompanies.push(company);
      }
    }

    setAddSuggestions(uniqueCompanies);
  }, [addSearchQuery, fuse]);

  const handleNavigateToCompany = (companyId) => {
    navigate(`/report/${companyId}`);
    setSearchQuery("");
    setSuggestions([]);
    setShowSuggestions(false);
  };

  const addToWatchlist = async (company) => {
    // Check if already in watchlist
    if (watchlist.some((c) => c.id === company.id)) {
      console.log("ℹ️ Company already in watchlist");
      setAddSearchQuery("");
      setAddSuggestions([]);
      setIsAddModalOpen(false);
      return;
    }

    try {
      const companyName = company.name || company.company_name || company.id;
      const companySymbol = company.ticker || company.id;

      console.log("📤 Sending add to watchlist:", {
        companyName,
        companySymbol,
        company,
      });

      // Optimistically add to watchlist immediately for better UX
      setWatchlist([...watchlist, company]);

      // Call backend to broadcast watchlist addition to all connected clients
      await api.addToWatchlist(companyName, companySymbol);
      console.log("✅ Add to watchlist request sent to backend");

      // Close modal and clear search
      setAddSearchQuery("");
      setAddSuggestions([]);
      setIsAddModalOpen(false);
    } catch (error) {
      console.error("❌ Failed to call backend add to watchlist:", error);
      // Already added optimistically, so no need to add again
      setAddSearchQuery("");
      setAddSuggestions([]);
      setIsAddModalOpen(false);
    }
  };

  const removeFromWatchlist = async (e, companyId) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      // Find company name for the backend call
      const company = watchlist.find((c) => c.id === companyId);
      const companyName = company?.name || company?.company_name || companyId;

      console.log("📤 Sending remove from watchlist:", companyName);

      // Optimistically remove from watchlist immediately for better UX
      setWatchlist(watchlist.filter((c) => c.id !== companyId));

      // Call backend to broadcast watchlist removal to all connected clients
      await api.removeFromWatchlist(companyName);
      console.log("✅ Remove from watchlist request sent to backend");
    } catch (error) {
      console.error("❌ Failed to call backend remove from watchlist:", error);
      // Already removed optimistically, so it's fine
    }
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case "Positive":
        return "bg-green-100 text-green-800";
      case "Negative":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const stripHtml = (html) => {
    if (!html) return "";
    const tmp = document.createElement("DIV");
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || "";
  };

  return (
    <div
      className={`min-h-screen ${
        theme === "dark"
          ? "bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950"
          : "bg-gradient-to-br from-gray-50 via-white to-gray-50"
      } relative`}
    >
      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center min-h-screen p-4">
          <div className="max-w-md w-full">
            {/* Loading Header */}
            <div className="text-center mb-8">
              <div className="relative inline-flex items-center justify-center mb-6">
                <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-green-500"></div>
                <Sparkles className="absolute w-6 h-6 text-green-400 animate-pulse" />
              </div>
              <h2 className={`text-2xl font-bold text-green-400 mb-2`}>
                Loading Dashboard
              </h2>
              <p className={theme === "dark" ? "text-slate-400" : "text-gray-600"}>
                Setting up your ESG intelligence platform...
              </p>
            </div>

            {/* Current Progress */}
            {currentLoadingStep && (
              <div className={`backdrop-blur-sm rounded-lg p-4 mb-4 border ${
                theme === "dark" 
                  ? "bg-slate-800/50 border-green-500/20" 
                  : "bg-white/80 border-green-500/30"
              }`}>
                <div className="flex items-center space-x-3">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-400"></div>
                  <p className="text-green-400 font-medium">{currentLoadingStep}</p>
                </div>
              </div>
            )}

            {/* Progress Steps */}
            {loadingSteps.length > 0 && (
              <div className="space-y-3">
                <h3 className={`text-sm font-semibold mb-3 ${
                  theme === "dark" ? "text-slate-300" : "text-gray-700"
                }`}>
                  Progress:
                </h3>
                {loadingSteps.map((step, index) => (
                  <div 
                    key={index}
                    className={`flex items-start space-x-3 rounded-lg p-3 border animate-slideIn ${
                      theme === "dark" 
                        ? "bg-slate-800/30 border-slate-700/50" 
                        : "bg-white/50 border-gray-300/50"
                    }`}
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      <div className="w-5 h-5 rounded-full bg-green-500/20 border-2 border-green-500 flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-green-400"></div>
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${
                        theme === "dark" ? "text-slate-300" : "text-gray-700"
                      }`}>
                        {step.message}
                      </p>
                      <p className={`text-xs mt-1 ${
                        theme === "dark" ? "text-slate-500" : "text-gray-500"
                      }`}>
                        {new Date(step.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Loading Animation */}
            <div className="mt-6 flex justify-center space-x-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex items-center justify-center min-h-screen p-4">
          <div
            className={`max-w-md p-6 rounded-lg ${
              theme === "dark"
                ? "bg-slate-800 text-white"
                : "bg-white text-gray-900"
            }`}
          >
            <h2 className="text-xl font-bold mb-2 text-red-500">
              Error Loading Data
            </h2>
            <p
              className={theme === "dark" ? "text-slate-300" : "text-gray-700"}
            >
              {error}
            </p>
            <p
              className={`mt-4 text-sm ${
                theme === "dark" ? "text-slate-400" : "text-gray-600"
              }`}
            >
              Make sure the backend server is running on port 5001.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Main Content - Only show when not loading and no error */}
      {!loading && !error && (
        <>
          {/* Animated background elements */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute top-20 left-20 w-96 h-96 bg-green-500/10 rounded-full blur-3xl animate-float"></div>
            <div
              className="absolute bottom-20 right-20 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-float"
              style={{ animationDelay: "1s" }}
            ></div>
            <div
              className="absolute top-1/2 left-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-float"
              style={{ animationDelay: "2s" }}
            ></div>
          </div>
          {/* Add Company Modal */}
          {isAddModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
              <div
                className={`w-full max-w-md p-6 rounded-2xl shadow-2xl ${
                  theme === "dark"
                    ? "bg-slate-900 border border-slate-700"
                    : "bg-white"
                } transform transition-all scale-100`}
              >
                <div className="flex justify-between items-center mb-6">
                  <h2
                    className={`text-2xl font-bold ${
                      theme === "dark" ? "text-white" : "text-gray-900"
                    }`}
                  >
                    Add to Watchlist
                  </h2>
                  <button
                    onClick={() => setIsAddModalOpen(false)}
                    className={`p-2 rounded-full ${
                      theme === "dark"
                        ? "hover:bg-slate-800 text-slate-400"
                        : "hover:bg-gray-100 text-gray-500"
                    }`}
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <div className="relative mb-6">
                  <input
                    type="text"
                    value={addSearchQuery}
                    onChange={(e) => setAddSearchQuery(e.target.value)}
                    placeholder="Search company name or ticker..."
                    autoFocus
                    className={`w-full px-4 py-3 rounded-xl border ${
                      theme === "dark"
                        ? "bg-slate-800 border-slate-600 text-white placeholder-slate-400 focus:border-green-500"
                        : "bg-gray-50 border-gray-300 text-gray-900 focus:border-green-500"
                    } focus:outline-none focus:ring-2 focus:ring-green-500/20 transition-all`}
                  />
                </div>

                <div
                  className={`max-h-60 overflow-y-auto rounded-xl ${
                    theme === "dark" ? "bg-slate-800/50" : "bg-gray-50"
                  } custom-scrollbar`}
                >
                  {addSearchQuery && addSuggestions.length > 0 ? (
                    addSuggestions.map((company) => (
                      <button
                        key={company.id}
                        onClick={() => addToWatchlist(company)}
                        className={`w-full px-4 py-3 flex items-center justify-between group transition-colors ${
                          theme === "dark"
                            ? "hover:bg-slate-700 text-slate-200"
                            : "hover:bg-gray-200 text-gray-700"
                        }`}
                      >
                        <div className="text-left">
                          <div className="font-semibold">{company.name}</div>
                          <div
                            className={`text-xs ${
                              theme === "dark"
                                ? "text-slate-400"
                                : "text-gray-500"
                            }`}
                          >
                            {company.id} • {company.industry}
                          </div>
                        </div>
                        {watchlist.some((c) => c.id === company.id) ? (
                          <span className="text-xs text-green-500 font-medium px-2 py-1 bg-green-500/10 rounded">
                            Added
                          </span>
                        ) : (
                          <Plus className="w-5 h-5 text-green-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                        )}
                      </button>
                    ))
                  ) : addSearchQuery ? (
                    <div
                      className={`p-4 text-center ${
                        theme === "dark" ? "text-slate-400" : "text-gray-500"
                      }`}
                    >
                      No companies found
                    </div>
                  ) : (
                    <div
                      className={`p-4 text-center ${
                        theme === "dark" ? "text-slate-500" : "text-gray-400"
                      }`}
                    >
                      Type to search...
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <div className="w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
            <div className="grid grid-cols-1 lg:grid-cols-[30%_40%_30%] 2xl:grid-cols-[32%_36%_32%] gap-6 lg:gap-8 min-h-[calc(100vh-8rem)]">
              {/* Left Column - Chat Sidebar */}
              <DashboardChatSidebar />

              {/* Middle Column - Main Content */}
              <main className="col-span-1 flex flex-col max-h-[calc(100vh-8rem)]">
                {/* Header Section */}
                <div className="mb-4">
                  <div className="flex items-center justify-between animate-slideIn mb-4">
                    <div>
                      <h1 className="text-2xl font-bold bg-gradient-to-r from-green-500 via-emerald-400 to-green-600 bg-clip-text text-transparent drop-shadow-2xl gradient-animate">
                        Sustainability Watchlist
                      </h1>
                      <div className="flex items-center gap-4 mt-1">
                        <p
                          className={`${
                            theme === "dark"
                              ? "text-slate-400"
                              : "text-slate-600"
                          } text-sm animate-fadeIn`}
                          style={{ animationDelay: "0.2s" }}
                        >
                          Track Companies' ESG Performance & Innovation
                        </p>
                        {lastUpdate && (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="flex h-2 w-2 relative">
                              <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-green-400 opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                            </span>
                            <span
                              className={
                                theme === "dark"
                                  ? "text-green-400"
                                  : "text-green-600"
                              }
                            >
                              Live • Updated {lastUpdate}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => setIsAddModalOpen(true)}
                      className="group relative flex items-center space-x-2 bg-gradient-to-r from-green-600 via-emerald-600 to-green-600 text-white px-4 py-2 rounded-lg shadow-lg shadow-green-500/40 hover:shadow-2xl hover:shadow-green-500/60 transition-all duration-300 hover:scale-105 overflow-hidden"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-green-500 via-emerald-500 to-green-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                      <Plus className="w-4 h-4 relative z-10 group-hover:rotate-90 transition-transform duration-300" />
                      <span className="font-semibold text-sm relative z-10">
                        Add Company
                      </span>
                    </button>
                  </div>

                  {/* Live Analytics Stats */}
                  {analytics && (
                    <div
                      className="grid grid-cols-3 gap-3 mb-4 animate-slideIn"
                      style={{ animationDelay: "0.15s" }}
                    >
                      <div
                        className={`p-3 rounded-lg ${
                          theme === "dark"
                            ? "bg-slate-800/60 border-green-500/30"
                            : "bg-white border-gray-200"
                        } border`}
                      >
                        <p
                          className={`text-xs ${
                            theme === "dark"
                              ? "text-slate-400"
                              : "text-gray-600"
                          } mb-0.5 uppercase tracking-wider`}
                        >
                          Total Projects
                        </p>
                        <p
                          className={`text-xl font-bold ${
                            theme === "dark"
                              ? "text-green-400"
                              : "text-green-600"
                          }`}
                        >
                          {analytics.projects?.total?.toLocaleString() || 0}
                        </p>
                      </div>
                      <div
                        className={`p-3 rounded-lg ${
                          theme === "dark"
                            ? "bg-slate-800/60 border-green-500/30"
                            : "bg-white border-gray-200"
                        } border`}
                      >
                        <p
                          className={`text-xs ${
                            theme === "dark"
                              ? "text-slate-400"
                              : "text-gray-600"
                          } mb-0.5 uppercase tracking-wider`}
                        >
                          Carbon Credits
                        </p>
                        <p
                          className={`text-xl font-bold ${
                            theme === "dark"
                              ? "text-green-400"
                              : "text-green-600"
                          }`}
                        >
                          {(
                            (analytics.projects?.total_supply || 0) / 1000000
                          ).toFixed(1)}
                          M
                        </p>
                      </div>
                      <div
                        className={`p-3 rounded-lg ${
                          theme === "dark"
                            ? "bg-slate-800/60 border-green-500/30"
                            : "bg-white border-gray-200"
                        } border`}
                      >
                        <p
                          className={`text-xs ${
                            theme === "dark"
                              ? "text-slate-400"
                              : "text-gray-600"
                          } mb-0.5 uppercase tracking-wider`}
                        >
                          Avg Price
                        </p>
                        <p
                          className={`text-xl font-bold ${
                            theme === "dark"
                              ? "text-green-400"
                              : "text-green-600"
                          }`}
                        >
                          ${(analytics.projects?.avg_price || 0).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Companies Grid - Scrollable */}
                <div
                  className="flex-1 overflow-y-auto pr-2 custom-scrollbar"
                  style={{ maxHeight: "calc(100vh - 20rem)" }}
                >
                  {watchlist.length === 0 ? (
                    <div
                      className={`flex flex-col items-center justify-center h-64 ${
                        theme === "dark" ? "text-slate-500" : "text-slate-400"
                      }`}
                    >
                      <p className="text-lg">Your watchlist is empty.</p>
                      <p className="text-sm mt-2">
                        Search for companies above to add them.
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-4">
                      {watchlist.map((company, idx) => (
                        <Link
                          key={company.id}
                          to={`/report/${company.id}`}
                          className={`group relative overflow-hidden ${
                            theme === "dark"
                              ? "bg-gradient-to-br from-slate-900/90 via-slate-800/90 to-slate-900/90 border-green-500/30"
                              : "bg-white border-gray-200"
                          } backdrop-blur-xl rounded-xl shadow-xl hover:shadow-green-500/40 transition-all duration-500 p-4 border hover:border-green-500 animate-slideIn hover-lift`}
                          style={{ animationDelay: `${0.2 + idx * 0.1}s` }}
                        >
                          {/* Animated gradient overlay */}
                          <div className="absolute inset-0 bg-gradient-to-br from-green-500/0 via-emerald-500/0 to-green-500/0 group-hover:from-green-500/10 group-hover:via-emerald-500/5 group-hover:to-green-500/10 transition-all duration-500"></div>

                          {/* Shimmer effect */}
                          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-green-400/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
                          </div>
                          <div className="flex justify-between items-start mb-3 relative z-10">
                            <div className="flex-1">
                              <h3
                                className={`text-lg font-bold ${
                                  theme === "dark"
                                    ? "text-green-300"
                                    : "text-green-700"
                                } group-hover:text-green-500 transition-all duration-300`}
                              >
                                {company.name}
                              </h3>
                              <p
                                className={`text-xs ${
                                  theme === "dark"
                                    ? "text-slate-400"
                                    : "text-slate-600"
                                } transition-colors duration-300`}
                              >
                                {company.industry}
                              </p>
                            </div>
                            <div className="flex items-center space-x-2">
                              <span className="bg-gradient-to-r from-green-600 via-emerald-600 to-green-600 text-white px-3 py-1 rounded-full text-xs font-bold shadow-lg shadow-green-500/40 group-hover:shadow-green-500/60 transition-all duration-300 group-hover:scale-105">
                                {company.id}
                              </span>
                              <button
                                onClick={(e) =>
                                  removeFromWatchlist(e, company.id)
                                }
                                className={`p-1.5 rounded-full ${
                                  theme === "dark"
                                    ? "hover:bg-red-500/20 text-slate-400 hover:text-red-400"
                                    : "hover:bg-red-100 text-slate-400 hover:text-red-600"
                                } transition-all duration-300 z-20`}
                                title="Remove from watchlist"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-3 mb-3 relative z-10">
                            <div
                              className={`p-2.5 rounded-lg ${
                                theme === "dark"
                                  ? "bg-slate-800/40 border-slate-700/50"
                                  : "bg-gray-50 border-gray-200"
                              } border group-hover:border-green-500/40 transition-all duration-300`}
                            >
                              <p
                                className={`text-xs ${
                                  theme === "dark"
                                    ? "text-slate-500"
                                    : "text-slate-600"
                                } mb-0.5 uppercase tracking-wider font-semibold`}
                              >
                                Stock Price
                              </p>
                              <p
                                className={`text-xl font-bold ${
                                  theme === "dark"
                                    ? "text-slate-200"
                                    : "text-slate-800"
                                } group-hover:text-green-600 transition-colors duration-300`}
                              >
                                $
                                {(
                                  company.stock_price ||
                                  company.price ||
                                  0
                                ).toFixed(2)}
                              </p>
                            </div>
                            <div
                              className={`p-2.5 rounded-lg ${
                                theme === "dark"
                                  ? "bg-slate-800/40 border-slate-700/50"
                                  : "bg-gray-50 border-gray-200"
                              } border group-hover:border-green-500/40 transition-all duration-300`}
                            >
                              <p
                                className={`text-xs ${
                                  theme === "dark"
                                    ? "text-slate-500"
                                    : "text-slate-600"
                                } mb-0.5 uppercase tracking-wider font-semibold`}
                              >
                                GII Score
                              </p>
                              <div className="flex items-center space-x-2">
                                <p
                                  className={`text-xl font-bold ${
                                    theme === "dark"
                                      ? "text-green-400"
                                      : "text-green-600"
                                  } transition-all duration-300`}
                                >
                                  {company.gii_score}
                                </p>
                                <span
                                  className={`text-xs ${
                                    theme === "dark"
                                      ? "bg-green-500/20 text-green-300 border-green-500/40"
                                      : "bg-green-100 text-green-700 border-green-300"
                                  } px-2 py-0.5 rounded-md border font-semibold`}
                                >
                                  {company.esg_rating}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="mt-3 relative z-10">
                            <p
                              className={`text-xs ${
                                theme === "dark"
                                  ? "text-slate-500"
                                  : "text-slate-600"
                              } line-clamp-2 transition-colors duration-300 leading-relaxed`}
                            >
                              {company.sustainability_update}
                            </p>
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </main>

              {/* Right Column - Live News */}
              <aside
                className="w-full lg:w-auto animate-slideIn"
                style={{ animationDelay: "0.3s" }}
              >
                <div
                  className={`${
                    theme === "dark"
                      ? "bg-gradient-to-br from-slate-900/95 via-slate-800/95 to-slate-900/95 border-green-500/30"
                      : "bg-white border-gray-200"
                  } backdrop-blur-xl rounded-2xl shadow-xl p-6 border`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <h2
                      className={`text-xl font-bold ${
                        theme === "dark"
                          ? "bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent"
                          : "text-green-700"
                      }`}
                    >
                      Live News Feed
                    </h2>
                    <span className="flex h-3 w-3 relative">
                      <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500 shadow-lg shadow-green-500/50"></span>
                    </span>
                  </div>

                  <div className="space-y-4 max-h-[calc(100vh-16rem)] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-green-500/50 scrollbar-track-transparent">
                    {Array.isArray(news) &&
                      news.map((article, idx) => (
                        <a
                          key={`${article.id || article.guid || "news"}-${idx}`}
                          href={article.link || article.url || "#"}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`group relative p-4 ${
                            theme === "dark"
                              ? "bg-slate-800/60 border-green-500/30"
                              : "bg-gray-50 border-gray-200"
                          } backdrop-blur-sm border rounded-xl hover:border-green-500 hover:shadow-lg hover:shadow-green-500/20 transition-all duration-300 cursor-pointer animate-slideIn overflow-hidden hover-lift block`}
                          style={{ animationDelay: `${0.4 + idx * 0.05}s` }}
                        >
                          {/* Hover shimmer effect */}
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-green-400/5 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>

                          <div className="flex items-start justify-between mb-2 relative z-10">
                            <span
                              className={`text-xs px-2.5 py-1 rounded-lg border font-semibold transition-all duration-300 ${
                                article.sentiment === "Positive"
                                  ? theme === "dark"
                                    ? "bg-green-500/20 text-green-300 border-green-500/40"
                                    : "bg-green-100 text-green-700 border-green-300"
                                  : article.sentiment === "Negative"
                                  ? theme === "dark"
                                    ? "bg-red-500/20 text-red-300 border-red-500/40"
                                    : "bg-red-100 text-red-700 border-red-300"
                                  : theme === "dark"
                                  ? "bg-slate-700/50 text-slate-300 border-slate-600/40"
                                  : "bg-gray-200 text-gray-700 border-gray-300"
                              }`}
                            >
                              {article.sentiment || "Neutral"}
                            </span>
                            <span
                              className={`text-xs ${
                                theme === "dark"
                                  ? "text-slate-500"
                                  : "text-slate-600"
                              } transition-colors duration-300`}
                            >
                              {formatDate(
                                article.date ||
                                  article.published ||
                                  new Date().toISOString()
                              )}
                            </span>
                          </div>

                          <h4
                            className={`font-bold ${
                              theme === "dark"
                                ? "text-slate-200 group-hover:text-green-300"
                                : "text-slate-800 group-hover:text-green-700"
                            } mb-2 transition-colors duration-300 line-clamp-2 relative z-10`}
                          >
                            {stripHtml(article.title)}
                          </h4>

                          <p
                            className={`text-sm ${
                              theme === "dark"
                                ? "text-slate-400"
                                : "text-slate-600"
                            } mb-3 line-clamp-2 transition-colors duration-300 relative z-10`}
                          >
                            {stripHtml(article.summary)}
                          </p>

                          <div className="flex items-center justify-between text-xs relative z-10">
                            <span
                              className={`${
                                theme === "dark"
                                  ? "text-slate-500 group-hover:text-green-400"
                                  : "text-slate-600 group-hover:text-green-600"
                              } transition-colors duration-300 font-medium`}
                            >
                              {article.source}
                            </span>
                            <ExternalLink
                              className={`w-3.5 h-3.5 ${
                                theme === "dark"
                                  ? "text-green-400"
                                  : "text-green-600"
                              } group-hover:scale-110 transition-transform duration-300`}
                            />
                          </div>
                        </a>
                      ))}

                    {/* Empty state */}
                    {(!news || news.length === 0) && (
                      <div
                        className={`text-center p-8 ${
                          theme === "dark" ? "text-slate-400" : "text-gray-600"
                        }`}
                      >
                        <p className="text-lg">No news available</p>
                        <p className="text-sm mt-2">
                          Check back later for updates
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;
