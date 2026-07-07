import React from 'react';

const AGENT_COLORS = {
  Planner:     'var(--amber)',
  NewsAgent:   'var(--blue)',
  MarketAgent: 'var(--green)',
  WebAgent:    'var(--purple)',
  Synthesizer: 'var(--text-primary)',
};

const STATUS_ICON = {
  routing:       '■',
  tool_call:     '→',
  tool_result:   '✓',
  synthesizing:  '◌',
  skipped:       '○',
  complete:      '✓',
  error:         '✕',
};

/**
 * AgentTracePanel — live streaming reasoning trace
 *
 * Props:
 *   streamUrl: string   — SSE endpoint URL
 *   onComplete: fn(html) — called when report is ready
 */
const AgentTracePanel = ({ id, streamUrl, onComplete }) => {
  const [steps, setSteps]     = React.useState(() => {
    try {
      const cached = sessionStorage.getItem(`trace_steps_${id}`);
      return cached ? JSON.parse(cached) : [];
    } catch { return []; }
  });
  const [streaming, setStreaming] = React.useState(false);
  const [done, setDone]       = React.useState(() => !!sessionStorage.getItem(`trace_steps_${id}`));
  const [error, setError]     = React.useState(null);
  const bottomRef             = React.useRef(null);
  const esRef                 = React.useRef(null);
  const startTimeRef          = React.useRef(null);

  // Auto-scroll to bottom as steps arrive
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [steps]);

  // Cleanup on unmount
  React.useEffect(() => {
    return () => { esRef.current?.close(); };
  }, []);

  // Update on ID change
  React.useEffect(() => {
    try {
      const cached = sessionStorage.getItem(`trace_steps_${id}`);
      if (cached) {
        setSteps(JSON.parse(cached));
        setDone(true);
      } else {
        setSteps([]);
        setDone(false);
      }
    } catch {}
  }, [id]);

  const start = () => {
    if (streaming) return;
    setSteps([]);
    setDone(false);
    setError(null);
    setStreaming(true);
    startTimeRef.current = performance.now();

    const es = new EventSource(streamUrl);
    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.step === 'done') {
          es.close();
          setStreaming(false);
          setDone(true);
          sessionStorage.setItem(`trace_steps_${id}`, JSON.stringify(stepsRef.current));
          return;
        }
        if (data.step === 'error') {
          es.close();
          setStreaming(false);
          setError(data.message || 'Unknown error');
          return;
        }
        if (data.step === 'complete' && data.report) {
          onComplete?.(data.report);
        }
        
        const elapsed = ((performance.now() - startTimeRef.current) / 1000).toFixed(1);
        const newData = { ...data, timeElapsed: `+${elapsed}s` };
        setSteps(prev => {
          const next = [...prev, newData];
          stepsRef.current = next;
          return next;
        });
      } catch {}
    };

    const stepsRef = { current: [] };

    es.onerror = () => {
      es.close();
      setStreaming(false);
      setError('Connection to agent stream lost');
    };
  };

  const reset = () => {
    esRef.current?.close();
    setSteps([]);
    setDone(false);
    setError(null);
    setStreaming(false);
    sessionStorage.removeItem(`trace_steps_${id}`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Control bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {!streaming && !done && (
          <button onClick={start} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px',
            background: 'var(--green)',
            color: '#000',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            fontWeight: 700,
            cursor: 'pointer',
            letterSpacing: '0.02em',
          }}>
            ⚡ Generate AI Analysis
          </button>
        )}
        {(streaming || done) && (
          <button onClick={reset} style={{
            padding: '5px 12px',
            background: 'none',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-muted)',
            fontSize: '11px',
            cursor: 'pointer',
          }}>
            ↺ Reset
          </button>
        )}
        {streaming && (
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            <span className="animate-blink" style={{ color: 'var(--green)', marginRight: 4 }}>●</span>
            Agents running...
          </span>
        )}
        {done && (
          <span style={{ fontSize: '11px', color: 'var(--green)' }}>✓ Complete</span>
        )}
      </div>

      {/* Trace panel */}
      {steps.length > 0 && (
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)',
          padding: '12px 14px',
          maxHeight: 320,
          overflowY: 'auto',
          fontFamily: 'var(--mono)',
        }}>
          {steps.map((step, i) => {
            const color  = AGENT_COLORS[step.agent] || 'var(--text-secondary)';
            const icon   = STATUS_ICON[step.step] || '·';
            const isCall = step.step === 'tool_call';
            const isRes  = step.step === 'tool_result';
            const isSkip = step.step === 'skipped';

            return (
              <div key={i} className="agent-step" style={{ marginBottom: 2 }}>
                <span className="agent-step-icon" style={{ color }}>
                  {step.step === 'synthesizing' || step.step === 'routing'
                    ? <span className="animate-spin" style={{ display: 'inline-block' }}>◌</span>
                    : icon}
                </span>
                <div className="agent-step-body" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
                    <span style={{ fontSize: '11px', fontWeight: 600, color }}>
                      {step.agent} <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 4 }}>{step.timeElapsed || ''}</span>
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {step.message || (isCall
                        ? `→ ${step.tool}(${JSON.stringify(step.input || '')})`
                        : isSkip ? step.message : '')}
                    </span>
                  </div>
                  {isRes && step.result && (
                    <div className="agent-step-detail" style={{ color: 'var(--text-secondary)' }}>
                      ↳ {step.result}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {streaming && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, fontSize: '11px', color: 'var(--text-muted)' }}>
              <span className="animate-spin" style={{ display: 'inline-block' }}>◌</span>
              <span>Waiting for next agent...</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {error && (
        <div style={{
          padding: '10px 14px',
          background: 'var(--red-dim)',
          border: '1px solid var(--red)',
          borderRadius: 'var(--radius-sm)',
          color: 'var(--red)',
          fontSize: '12px',
        }}>
          ✕ {error}
        </div>
      )}
    </div>
  );
};

export default AgentTracePanel;
