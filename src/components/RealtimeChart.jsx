import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../services/api';
import { fmtTickerPrice } from '../utils/currency';


const RealtimeChart = ({ currentPrice, symbol }) => {
  const [dataPoints, setDataPoints] = useState([]);
  const [minPrice, setMinPrice] = useState(0);
  const [maxPrice, setMaxPrice] = useState(0);
  const bufferSize = 100;

  // Fetch historical data on mount to backfill the chart
  useEffect(() => {
    if (!symbol) return;
    
    fetch(`${API_BASE_URL}/api/company/${symbol}/history`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.prices && data.prices.length > 0) {
          const history = data.prices.slice(-bufferSize);
          // If we already have a live currentPrice, make sure it's the very last point!
          setDataPoints(currentPrice ? [...history, parseFloat(currentPrice)] : history);
        }
      })
      .catch(err => console.error('Failed to fetch history:', err));
  }, [symbol]);

  useEffect(() => {
    if (currentPrice === null || currentPrice === undefined) return;
    
    const value = parseFloat(currentPrice);

    setDataPoints(prev => {
      const newPoints = [...prev, value];
      if (newPoints.length > bufferSize) {
        newPoints.shift();
      }
      return newPoints;
    });
  }, [currentPrice]);
  


  useEffect(() => {
    if (dataPoints.length > 0) {
      const min = Math.min(...dataPoints);
      const max = Math.max(...dataPoints);
      const padding = (max - min) * 0.2 || 1; // 20% padding
      setMinPrice(min - padding);
      setMaxPrice(max + padding);
    }
  }, [dataPoints]);

  if (dataPoints.length === 0) {
    return (
      <div style={{ height: '240px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        Waiting for live market data...
      </div>
    );
  }

  const width = 400;
  const height = 200;
  
  // If history fetch fails and we only have 1 point, duplicate it to draw a flat line
  const displayPoints = dataPoints.length === 1 ? [dataPoints[0], dataPoints[0]] : dataPoints;
  const pointCount = Math.max(displayPoints.length - 1, 1);
  const points = displayPoints.map((val, i) => {
    const x = (i / pointCount) * width;
    const y = height - ((val - minPrice) / (maxPrice - minPrice)) * height;
    return `${x},${y}`;
  }).join(' ');

  // Calculate area under the line for the gradient
  const areaPoints = `0,${height} ${points} ${width},${height}`;

  const latestPrice = displayPoints[displayPoints.length - 1];
  const startPrice = displayPoints[0];
  const isPositive = latestPrice >= startPrice;
  const color = isPositive ? '#16a34a' : '#dc2626'; // Green or Red
  const gradientId = `chart-gradient-${symbol}`;

  return (
    <div style={{ 
      position: 'relative', 
      height: '100%', 
      width: '100%', 
      display: 'flex', 
      flexDirection: 'column' 
    }}>
      <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h3 style={{ margin: 0, fontSize: '14px', color: 'var(--text-secondary)' }}>Live Market Chart</h3>
        <div style={{ textAlign: 'right' }}>
          <div className="mono" style={{ fontSize: '24px', fontWeight: 600, color: 'var(--text-primary)' }}>
            {fmtTickerPrice(latestPrice, symbol)}
          </div>
          <div className="mono" style={{ fontSize: '12px', color }}>
            {isPositive ? '▲' : '▼'} {Math.abs(latestPrice - startPrice).toFixed(2)} ({(Math.abs(latestPrice - startPrice) / startPrice * 100).toFixed(2)}%)
          </div>
        </div>
      </div>
      
      <div style={{ flex: 1, position: 'relative' }}>
        <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.3" />
              <stop offset="100%" stopColor={color} stopOpacity="0.0" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Grid lines */}
          <line x1="0" y1={height * 0.25} x2={width} y2={height * 0.25} stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="4 4" />
          <line x1="0" y1={height * 0.50} x2={width} y2={height * 0.50} stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="4 4" />
          <line x1="0" y1={height * 0.75} x2={width} y2={height * 0.75} stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="4 4" />

          {/* Area fill */}
          <polygon points={areaPoints} fill={`url(#${gradientId})`} />

          {/* Line */}
          <polyline 
            points={points} 
            fill="none" 
            stroke={color} 
            strokeWidth="2.5" 
            filter="url(#glow)"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          
          {/* Pulsing dot at the end */}
          <circle 
            cx={width} 
            cy={height - ((latestPrice - minPrice) / (maxPrice - minPrice)) * height} 
            r="4" 
            fill={color} 
            filter="url(#glow)"
          >
            <animate attributeName="r" values="4;6;4" dur="1.5s" repeatCount="indefinite" />
          </circle>
        </svg>
      </div>
    </div>
  );
};

export default RealtimeChart;
