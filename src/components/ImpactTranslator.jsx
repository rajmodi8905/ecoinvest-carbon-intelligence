import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { API_BASE_URL } from '../services/api';

const ImpactTranslator = ({ projectId }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [hasStarted, setHasStarted] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    const cached = localStorage.getItem(`impact_${projectId}`);
    if (cached) {
      setContent(cached);
      setHasStarted(true);
    } else {
      setContent('');
      setHasStarted(false);
      setLoading(false);
      setError(null);
    }
  }, [projectId]);

  const generateImpact = () => {
    setHasStarted(true);
    setLoading(true);
    setError(null);
    setContent('');

    const eventSource = new EventSource(`${API_BASE_URL}/api/llm/impact/${projectId}`);
    let currentContent = '';

    eventSource.onmessage = (event) => {
      try {
        if (event.data === '[DONE]') {
          eventSource.close();
          setLoading(false);
          localStorage.setItem(`impact_${projectId}`, currentContent);
          return;
        }

        const data = JSON.parse(event.data);
        if (data.content) {
          currentContent += data.content;
          setContent(prev => prev + data.content);
        }
      } catch (err) {
        console.error("Failed to parse SSE data", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      eventSource.close();
      setLoading(false);
      
      if (!currentContent) {
          setError("Failed to load Impact Translation");
      } else {
          localStorage.setItem(`impact_${projectId}`, currentContent);
      }
    };
  };

  return (
    <div className="panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: '300px' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Real-World Impact Translator</h3>
        {loading && <div style={{ fontSize: '10px', color: 'var(--green)' }}>● STREAMING</div>}
      </div>
      <div style={{ padding: '16px 20px', flex: 1, overflowY: 'auto' }}>
        {!hasStarted ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <button 
              onClick={generateImpact}
              style={{
                background: 'var(--green)',
                color: 'var(--bg-card)',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '6px',
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'inherit',
                fontSize: '13px'
              }}
            >
              Generate AI Analysis
            </button>
          </div>
        ) : error ? (
            <div style={{ color: 'var(--red)', fontSize: '13px' }}>{error}</div>
        ) : (
            <div className="markdown-body" style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6 }}>
                <ReactMarkdown>{content}</ReactMarkdown>
                {loading && <span className="blinking-cursor" style={{ display: 'inline-block', width: '8px', height: '1em', backgroundColor: 'var(--green)', marginLeft: '4px', verticalAlign: 'middle', animation: 'blink 1s step-end infinite' }}></span>}
            </div>
        )}
      </div>
    </div>
  );
};

export default ImpactTranslator;
