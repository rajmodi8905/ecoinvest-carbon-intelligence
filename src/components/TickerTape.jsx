import React from 'react';

// Scrolling equity ticker tape — pinned above the navbar
const TickerTape = ({ companies = [] }) => {
  if (!companies.length) return (
    <div style={{
      height: 'var(--ticker-h)',
      background: '#050505',
      borderBottom: '1px solid var(--border)',
    }} />
  );

  // Build display items
  const items = companies.map(c => ({
    ticker: c.ticker || c.id || '',
    price: parseFloat(c.price || c.stock_price || 0).toFixed(2),
    change: parseFloat(c.change_percent || 0),
  })).filter(c => c.ticker);

  // Duplicate for seamless loop
  const doubled = [...items, ...items];

  return (
    <div style={{
      height: 'var(--ticker-h)',
      background: '#050505',
      borderBottom: '1px solid var(--border)',
      overflow: 'hidden',
      position: 'sticky',
      top: 0,
      zIndex: 110,
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        height: '100%',
        width: 'max-content',
        animation: `ticker-scroll ${Math.max(40, items.length * 3)}s linear infinite`,
        willChange: 'transform',
      }}>
        {doubled.map((item, i) => (
          <span
            key={i}
            className="mono"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '0 18px',
              fontSize: '11px',
              whiteSpace: 'nowrap',
              borderRight: '1px solid var(--border)',
            }}
          >
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{item.ticker}</span>
            <span style={{ color: 'var(--text-primary)' }}>{item.price}</span>
            <span style={{ color: item.change >= 0 ? 'var(--green)' : 'var(--red)' }}>
              {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  );
};

export default TickerTape;
