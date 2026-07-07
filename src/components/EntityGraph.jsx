import React from 'react';

/**
 * EntityGraph — force-directed knowledge graph
 * Shows: Company ↔ News ↔ Macro theme ↔ Related project
 *
 * Rendered as a simple canvas-free SVG force simulation.
 * Uses built-in browser APIs only — no d3 dependency.
 *
 * Props:
 *   ticker: string
 *   macroThemes: array of matched theme names
 *   newsArticles: array of news items
 *   relatedProjects: array of project items
 *   onNodeClick: fn(node)
 */
const EntityGraph = ({ ticker, macroThemes = [], newsArticles = [], relatedProjects = [], onNodeClick }) => {
  const canvasRef = React.useRef(null);
  const animRef   = React.useRef(null);
  const nodesRef  = React.useRef([]);
  const edgesRef  = React.useRef([]);

  // ── Build graph data ──────────────────────────────────────────────────────
  React.useEffect(() => {
    const W = canvasRef.current?.clientWidth || 600;
    const H = 280;

    const cx = W / 2, cy = H / 2;

    // Company node (center)
    const nodes = [{
      id: ticker, label: ticker, type: 'company',
      x: cx, y: cy, vx: 0, vy: 0, r: 20,
      color: 'var(--green)',
    }];

    const edges = [];

    // News nodes (up to 5) — clustered top-left
    const newsSlice = newsArticles.slice(0, 5);
    newsSlice.forEach((a, i) => {
      const angle = (Math.PI / 2) + (i - newsSlice.length / 2) * 0.6;
      const dist  = 110 + Math.random() * 30;
      nodes.push({
        id: `news-${i}`, label: a.source || 'News', type: 'news',
        x: cx + Math.cos(angle) * dist * 0.7,
        y: cy - Math.abs(Math.sin(angle) * dist),
        vx: 0, vy: 0, r: 9,
        color: 'var(--blue)',
        data: a,
      });
      edges.push({ source: ticker, target: `news-${i}` });
    });

    // Theme nodes (up to 3) — right side
    macroThemes.slice(0, 3).forEach((theme, i) => {
      const angle = -Math.PI / 4 + i * 0.7;
      nodes.push({
        id: `theme-${i}`, label: theme, type: 'theme',
        x: cx + Math.cos(angle) * 140,
        y: cy + Math.sin(angle) * 90,
        vx: 0, vy: 0, r: 14,
        color: 'var(--amber)',
        data: { theme },
      });
      edges.push({ source: ticker, target: `theme-${i}` });
    });

    // Project nodes (up to 3) — bottom
    relatedProjects.slice(0, 3).forEach((p, i) => {
      const angle = Math.PI / 2 + (i - 1) * 0.5;
      nodes.push({
        id: `proj-${i}`, label: p.project_id || p.id || 'Proj', type: 'project',
        x: cx + Math.cos(angle) * 120,
        y: cy + Math.abs(Math.sin(angle) * 100),
        vx: 0, vy: 0, r: 9,
        color: '#22d3ee',
        data: p,
      });
      // connect to shared theme
      if (macroThemes.length > 0) {
        edges.push({ source: `theme-0`, target: `proj-${i}` });
      } else {
        edges.push({ source: ticker, target: `proj-${i}` });
      }
    });

    nodesRef.current = nodes;
    edgesRef.current = edges;
    startAnimation(W, H);

    return () => { cancelAnimationFrame(animRef.current); };
  }, [ticker, macroThemes.length, newsArticles.length, relatedProjects.length]);

  const startAnimation = (W, H) => {
    cancelAnimationFrame(animRef.current);

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width  = W;
    canvas.height = H;

    const tick = () => {
      const nodes = nodesRef.current;
      const edges = edgesRef.current;

      // Simple force simulation (no d3)
      // Repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const dist = Math.sqrt(dx*dx + dy*dy) || 1;
          const force = 800 / (dist * dist);
          const fx = force * dx / dist;
          const fy = force * dy / dist;
          nodes[i].vx -= fx; nodes[i].vy -= fy;
          nodes[j].vx += fx; nodes[j].vy += fy;
        }
      }

      // Attraction to center for company node
      const center = nodes[0];
      const pullX = (W/2 - center.x) * 0.005;
      const pullY = (H/2 - center.y) * 0.005;
      center.vx += pullX; center.vy += pullY;

      // Spring edges
      const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
      for (const e of edges) {
        const s = nodeMap[e.source], t = nodeMap[e.target];
        if (!s || !t) continue;
        const dx = t.x - s.x, dy = t.y - s.y;
        const dist = Math.sqrt(dx*dx+dy*dy)||1;
        const force = (dist - 120) * 0.012;
        const fx = force * dx / dist, fy = force * dy / dist;
        s.vx += fx; s.vy += fy;
        t.vx -= fx; t.vy -= fy;
      }

      // Integrate + damp + clamp
      for (const n of nodes) {
        if (n.id === ticker) continue; // don't move center
        n.vx *= 0.85; n.vy *= 0.85;
        n.x += n.vx; n.y += n.vy;
        n.x = Math.max(n.r+8, Math.min(W-n.r-8, n.x));
        n.y = Math.max(n.r+8, Math.min(H-n.r-8, n.y));
      }

      // Draw
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#111111';
      ctx.fillRect(0, 0, W, H);

      // Edges
      for (const e of edges) {
        const s = nodeMap[e.source], t = nodeMap[e.target];
        if (!s || !t) continue;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
        ctx.strokeStyle = '#2a2a2a';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Nodes
      for (const n of nodes) {
        // resolve CSS var to actual color
        const color = n.color
          .replace('var(--green)', '#00d26a')
          .replace('var(--blue)', '#3b82f6')
          .replace('var(--amber)', '#f0c040')
          .replace('var(--text-primary)', '#e8e8e8');

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI*2);
        ctx.fillStyle = color + '22';
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = n.type === 'company' ? 2 : 1.5;
        ctx.stroke();

        ctx.fillStyle = color;
        ctx.font = `${n.type === 'company' ? '600 12px' : '500 9px'} 'JetBrains Mono', monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(n.label, n.x, n.y);
      }

      animRef.current = requestAnimationFrame(tick);
    };

    tick();
  };

  const handleClick = (evt) => {
    if (!onNodeClick) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const mx = evt.clientX - rect.left;
    const my = evt.clientY - rect.top;
    for (const n of nodesRef.current) {
      const dx = mx - n.x, dy = my - n.y;
      if (dx*dx + dy*dy <= n.r * n.r * 1.5) {
        onNodeClick(n);
        break;
      }
    }
  };

  return (
    <div className="graph-wrapper" style={{ position: 'relative' }}>
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Entity Graph
        </span>
        <div style={{ display: 'flex', gap: 10 }}>
          {[
            ['Company', 'var(--green)'],
            ['News',    'var(--blue)'],
            ['Theme',   'var(--amber)'],
            ['Project', '#22d3ee'],
          ].map(([label, color]) => (
            <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '9px', color: 'var(--text-muted)' }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, display: 'inline-block' }} />
              {label}
            </span>
          ))}
        </div>
      </div>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: 280, display: 'block', cursor: onNodeClick ? 'pointer' : 'default' }}
        onClick={handleClick}
      />
    </div>
  );
};

export default EntityGraph;
