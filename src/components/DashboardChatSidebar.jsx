import React from "react";
import { Bot, Send, Sparkles } from "lucide-react";
import { ThemeContext } from "../context/ThemeContext";
import ReactMarkdown from "react-markdown";
import * as api from "../services/api";

const DashboardChatSidebar = () => {
  const { theme } = React.useContext(ThemeContext);
  const [messages, setMessages] = React.useState([
    {
      from: "bot",
      text: "Hi — I'm EcoInvest AI. Ask about your watchlist, reports, or recent sustainability news.",
    },
  ]);
  const [input, setInput] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [sessionId] = React.useState(
    () => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  );
  const messagesEndRef = React.useRef(null);

  // Auto-scroll to latest message
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const suggested = [
    "What are the current companies on my watchlist?",
    "Add Tesla to Watchlist",
    "Generate report on Tesla",
    "News related to sustainability",
  ];

  const sendMessage = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { from: "user", text: userMessage }]);
    setInput("");
    setIsLoading(true);

    try {
      // Call Flask backend API using api service
      const response = await api.sendChatMessage(userMessage, sessionId);

      if (response.success) {
        setMessages((prev) => [
          ...prev,
          { from: "bot", text: response.response },
        ]);
      } else {
        const friendly =
          response.error ||
          response.response ||
          "Sorry, I encountered an error. Please try again.";
        setMessages((prev) => [
          ...prev,
          {
            from: "bot",
            text: friendly,
          },
        ]);
      }
    } catch (error) {
      console.error("Error calling AI bot:", error);
      setMessages((prev) => [
        ...prev,
        {
          from: "bot",
          text: "Sorry, I'm having trouble connecting to the AI service. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const onSuggest = async (text) => {
    if (isLoading) return;
    setInput(text);
    setMessages((prev) => [...prev, { from: "user", text }]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await api.sendChatMessage(text, sessionId);

      if (response.success) {
        setMessages((prev) => [
          ...prev,
          { from: "bot", text: response.response },
        ]);
      } else {
        const friendly =
          response.error ||
          response.response ||
          "Sorry, I encountered an error. Please try again.";
        setMessages((prev) => [
          ...prev,
          {
            from: "bot",
            text: friendly,
          },
        ]);
      }
    } catch (error) {
      console.error("Error calling AI bot:", error);
      setMessages((prev) => [
        ...prev,
        {
          from: "bot",
          text: "Sorry, I'm having trouble connecting to the AI service. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <aside className="hidden lg:block w-full">
      <div
        className={`${
          theme === "dark"
            ? "bg-gradient-to-br from-slate-900/95 via-slate-800/95 to-slate-900/95 border-green-500/30"
            : "bg-white border-gray-200"
        } backdrop-blur-xl shadow-xl rounded-2xl border animate-slideIn sticky top-24`}
      >
        <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-green-600 via-emerald-600 to-green-600 text-white relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse"></div>
          <Bot className="w-5 h-5 relative z-10 drop-shadow-lg" />
          <h3 className="font-semibold relative z-10 drop-shadow-lg">
            EcoInvest AI
          </h3>
        </div>

        <div className="h-[calc(100vh-10rem)] flex flex-col p-4">
          {/* Message history - Fixed height with scrolling */}
          <div className="flex-1 min-h-0 overflow-y-auto space-y-3 mb-3 pr-2 scrollbar-thin scrollbar-thumb-green-500/50 scrollbar-track-transparent">
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.from === "user" ? "flex justify-end" : "flex justify-start"
                }
              >
                <div
                  className={`${
                    m.from === "user"
                      ? "bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-lg shadow-green-500/50"
                      : theme === "dark"
                      ? "bg-slate-800/80 border border-slate-700/50 text-slate-200"
                      : "bg-gray-50 border border-gray-200 text-slate-800"
                  } px-3 py-2 rounded-lg max-w-[85%] backdrop-blur-sm animate-slideIn`}
                >
                  {m.from === "bot" ? (
                    <div
                      className={`text-sm prose prose-sm max-w-none ${
                        theme === "dark"
                          ? "prose-invert prose-headings:text-green-400 prose-strong:text-green-300 prose-a:text-green-400 prose-code:text-green-300"
                          : "prose-headings:text-green-700 prose-strong:text-green-700 prose-a:text-green-600 prose-code:text-green-600"
                      } prose-strong:font-bold prose-ul:list-disc prose-ul:ml-4 prose-li:my-0.5 prose-p:my-2 prose-p:leading-relaxed`}
                      dangerouslySetInnerHTML={{ __html: m.text }}
                    />
                  ) : (
                    <p className="text-sm">{m.text}</p>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggested Functions - Compact design */}
          <div className="mb-3 flex-shrink-0">
            <details className="group" open>
              <summary
                className={`flex items-center gap-2 text-xs font-semibold ${
                  theme === "dark" ? "text-green-400" : "text-green-600"
                } mb-2 cursor-pointer select-none list-none`}
              >
                <Sparkles
                  className={`w-3.5 h-3.5 ${
                    theme === "dark" ? "text-green-400" : "text-green-600"
                  } animate-pulse`}
                />
                <span>Quick Actions</span>
                <svg
                  className="w-3 h-3 transition-transform group-open:rotate-180"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </summary>
              <div className="grid grid-cols-2 gap-1.5 max-h-32 overflow-y-auto scrollbar-thin scrollbar-thumb-green-500/30 scrollbar-track-transparent pr-1">
                {suggested.map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSuggest(s)}
                    disabled={isLoading}
                    className={`text-left text-xs px-2 py-1.5 ${
                      theme === "dark"
                        ? "bg-slate-800/50 hover:bg-slate-700/50 text-slate-300 border-green-500/30"
                        : "bg-gray-50 hover:bg-gray-100 text-slate-700 border-gray-200"
                    } border rounded-md hover:border-green-500 transition-all ${
                      isLoading ? "opacity-50 cursor-not-allowed" : ""
                    }`}
                    title={s}
                  >
                    <span className="line-clamp-2">{s}</span>
                  </button>
                ))}
              </div>
            </details>
          </div>

          {/* Input - Fixed at bottom */}
          <form
            onSubmit={sendMessage}
            className={`pt-3 border-t ${
              theme === "dark" ? "border-green-500/20" : "border-gray-200"
            } flex-shrink-0`}
          >
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask EcoInvest AI..."
                disabled={isLoading}
                className={`flex-1 px-3 py-2 text-sm ${
                  theme === "dark"
                    ? "bg-slate-800/50 text-slate-200 placeholder-slate-500 border-green-500/30"
                    : "bg-white text-slate-800 placeholder-slate-500 border-gray-300"
                } border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 backdrop-blur-sm ${
                  isLoading ? "opacity-50 cursor-not-allowed" : ""
                }`}
              />
              <button
                type="submit"
                disabled={isLoading}
                className={`bg-gradient-to-r from-green-600 to-emerald-600 text-white p-2 rounded-lg hover:shadow-lg hover:shadow-green-500/50 transition-all hover:scale-105 ${
                  isLoading ? "opacity-50 cursor-not-allowed" : ""
                }`}
              >
                {isLoading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </aside>
  );
};

export default DashboardChatSidebar;
