import React from 'react';

// Blinking LIVE indicator dot
const LiveDot = ({ ms }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
    <span
      className="animate-blink"
      style={{
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        background: 'var(--green)',
        display: 'inline-block',
        flexShrink: 0,
      }}
    />
    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--mono)' }}>
      {ms != null ? `${ms}ms` : 'Live'}
    </span>
  </div>
);

export default LiveDot;
