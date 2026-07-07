import React from 'react';

// Bloomberg KPI stat card
const StatCard = ({ label, value, sublabel, valueColor }) => (
  <div className="stat-card">
    <div className="stat-label">{label}</div>
    <div className="stat-value" style={valueColor ? { color: valueColor } : {}}>
      {value}
    </div>
    {sublabel && <div className="stat-sub">{sublabel}</div>}
  </div>
);

export default StatCard;
