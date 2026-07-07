import React from 'react';
import ReactMarkdown from 'react-markdown';
import { MessageSquare, X, Send, Bot, User, Sparkles, Settings2 } from 'lucide-react';
import * as api from '../services/api';

const DEFAULT_PROMPTS = [
  "Analyze FuelCell Energy's live market risk",
  "Compare VCS-191 pricing to market floor",
  "Summarize today's Renewable Energy news",
  "What's the overall market sentiment?",
];

const AIChat = () => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [messages, setMessages] = React.useState([
    { role: 'assistant', content: 'Hi! I am your AI analyst. Ask me anything about the carbon market, equities, or news.' }
  ]);
  const [input, setInput] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [sessionId, setSessionId] = React.useState(null);
  
  // LLM settings
  const [provider, setProvider] = React.useState('Ollama'); // 'Ollama' | 'Gemini'
  const [geminiKey, setGeminiKey] = React.useState(localStorage.getItem('gemini_key') || '');
  const [status, setStatus] = React.useState(null);

  const scrollRef = React.useRef(null);

  React.useEffect(() => {
    // Check backend status
    fetch('http://localhost:5001/api/status')
      .then(r => r.json())
      .then(d => setStatus(d))
      .catch(() => {});
  }, [isOpen]);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading, provider]);

  const handleSend = async (text = input) => {
    if (!text.trim() || loading) return;
    
    // Save Gemini key
    if (provider === 'Gemini' && geminiKey) {
      localStorage.setItem('gemini_key', geminiKey);
    }

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.sendChatMessage(text, sessionId);
      if (res.session_id) setSessionId(res.session_id);
      
      let reply = res.response;
      if (res.status === 429) {
        reply = "⚠️ API limit reached. If using Gemini, please check your quota or try local Ollama.";
      } else if (!res.ok) {
        reply = "⚠️ Error generating response.";
      }

      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: "⚠️ Network error." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating button */}
      {!isOpen && (
        <button className="chat-fab" onClick={() => setIsOpen(true)}>
          <Sparkles size={16} style={{ color: '#000' }} />
          Ask AI
        </button>
      )}

      {/* Chat Drawer */}
      {isOpen && (
        <div className="chat-drawer">
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 16px', borderBottom: '1px solid var(--border)', background: 'var(--surface-2)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ background: 'var(--green-dim)', padding: 6, borderRadius: '50%' }}>
                <Bot size={16} color="var(--green)" />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>AI Analyst</span>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Context-aware insights</span>
              </div>
            </div>
            <button onClick={() => setIsOpen(false)} style={{ color: 'var(--text-muted)' }}>
              <X size={18} />
            </button>
          </div>

          {/* Settings / Provider Toggle */}
          <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)' }}>
            <div style={{ display: 'flex', gap: 0, borderRadius: 4, overflow: 'hidden', border: '1px solid var(--border)' }}>
              <button 
                onClick={() => setProvider('Ollama')}
                style={{
                  flex: 1, padding: '6px 0', fontSize: '11px', fontWeight: 600,
                  background: provider === 'Ollama' ? 'var(--surface-hover)' : 'var(--surface)',
                  color: provider === 'Ollama' ? 'var(--text-primary)' : 'var(--text-muted)',
                  borderRight: '1px solid var(--border)'
                }}
              >
                Local Ollama
              </button>
              <button 
                onClick={() => setProvider('Gemini')}
                style={{
                  flex: 1, padding: '6px 0', fontSize: '11px', fontWeight: 600,
                  background: provider === 'Gemini' ? 'var(--surface-hover)' : 'var(--surface)',
                  color: provider === 'Gemini' ? 'var(--text-primary)' : 'var(--text-muted)',
                }}
              >
                Gemini API
              </button>
            </div>
            
            {provider === 'Ollama' && (
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                <span>Model: {status?.ai_config?.llm_model || 'Loading...'}</span>
                {status?.ai_config?.provider === 'ollama' ? <span style={{color: 'var(--green)'}}>Connected</span> : <span style={{color: 'var(--red)'}}>Disconnected</span>}
              </div>
            )}
            
            {provider === 'Gemini' && (
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Settings2 size={12} color="var(--text-muted)" />
                <input
                  type="password"
                  placeholder="Paste Gemini API Key..."
                  value={geminiKey}
                  onChange={e => setGeminiKey(e.target.value)}
                  style={{
                    flex: 1, background: 'var(--bg)', border: '1px solid var(--border)', 
                    borderRadius: 3, padding: '4px 8px', fontSize: '11px', color: 'var(--text-primary)'
                  }}
                />
              </div>
            )}
          </div>

          {/* Messages */}
          <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 16 }}>
            {messages.map((msg, idx) => (
              <div key={idx} style={{
                display: 'flex', gap: 12, alignItems: 'flex-start',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
              }}>
                <div style={{
                  width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: msg.role === 'user' ? 'var(--surface-hover)' : 'var(--green-dim)',
                  color: msg.role === 'user' ? 'var(--text-secondary)' : 'var(--green)'
                }}>
                  {msg.role === 'user' ? <User size={12} /> : <Bot size={12} />}
                </div>
                <div style={{
                  background: msg.role === 'user' ? 'var(--surface-hover)' : 'none',
                  border: msg.role === 'user' ? '1px solid var(--border)' : 'none',
                  padding: msg.role === 'user' ? '8px 12px' : 0,
                  borderRadius: msg.role === 'user' ? '8px 8px 0px 8px' : 0,
                  fontSize: '12px', lineHeight: 1.5,
                  color: msg.role === 'user' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  maxWidth: '85%'
                }}>
                  {msg.role === 'user' ? (
                    msg.content
                  ) : (
                    <ReactMarkdown components={{
                      p: ({node, ...props}) => <p style={{ marginBottom: '0.7em', marginTop: 0 }} {...props} />,
                      ul: ({node, ...props}) => <ul style={{ paddingLeft: '1.2em', marginBottom: '0.7em', marginTop: 0 }} {...props} />,
                      li: ({node, ...props}) => <li style={{ marginBottom: '0.2em' }} {...props} />,
                    }}>
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </div>
              </div>
            ))}
            
            {loading && (
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--green-dim)', color: 'var(--green)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Bot size={12} />
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', gap: 4, alignItems: 'center', height: 24 }}>
                  <span className="animate-blink" style={{ animationDelay: '0ms' }}>●</span>
                  <span className="animate-blink" style={{ animationDelay: '200ms' }}>●</span>
                  <span className="animate-blink" style={{ animationDelay: '400ms' }}>●</span>
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
            {messages.length === 1 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
                {DEFAULT_PROMPTS.map((p, i) => (
                  <button key={i} onClick={() => handleSend(p)} style={{
                    padding: '4px 8px', fontSize: '10px', background: 'var(--surface-hover)', 
                    border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-secondary)',
                    cursor: 'pointer', textAlign: 'left'
                  }}>
                    {p}
                  </button>
                ))}
              </div>
            )}
            
            <form 
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              style={{ display: 'flex', alignItems: 'center', gap: 8 }}
            >
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask about live data, news, or analysis..."
                style={{
                  flex: 1, padding: '10px 14px', borderRadius: 20,
                  background: 'var(--bg)', border: '1px solid var(--border)',
                  color: 'var(--text-primary)', fontSize: '12px'
                }}
              />
              <button 
                type="submit" 
                disabled={!input.trim() || loading || (provider==='Gemini' && !geminiKey)}
                style={{
                  width: 36, height: 36, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: (!input.trim() || loading || (provider==='Gemini' && !geminiKey)) ? 'var(--surface-hover)' : 'var(--green)',
                  color: (!input.trim() || loading || (provider==='Gemini' && !geminiKey)) ? 'var(--text-muted)' : '#000',
                  border: 'none', cursor: (!input.trim() || loading || (provider==='Gemini' && !geminiKey)) ? 'default' : 'pointer'
                }}
              >
                <Send size={14} style={{ marginLeft: 2 }} />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default AIChat;
