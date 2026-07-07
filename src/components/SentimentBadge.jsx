import React from 'react';

// Inline sentiment badge: "Positive +0.12" / "Negative -0.19" / "Neutral +0.00"
const SentimentBadge = ({ label, score }) => {
  const isPos = label === 'Positive';
  const isNeg = label === 'Negative';

  const cls = isPos ? 'badge-green' : isNeg ? 'badge-red' : 'badge-muted';
  const scoreStr = score != null
    ? ` ${score >= 0 ? '+' : ''}${parseFloat(score).toFixed(2)}`
    : '';

  return (
    <span className={`badge ${cls}`}>
      {label}{scoreStr}
    </span>
  );
};

export default SentimentBadge;
