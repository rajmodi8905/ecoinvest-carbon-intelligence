import React from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

/**
 * TerminalTable — reusable Bloomberg-style dense data table
 *
 * columns: Array<{
 *   key: string,
 *   label: string,
 *   width?: string | number,
 *   align?: 'left' | 'right' | 'center',
 *   render?: (value, row) => ReactNode,
 *   sortable?: boolean,
 * }>
 *
 * data: Array<object>
 * onRowClick?: (row) => void
 * defaultSort?: string  (column key)
 * defaultDir?: 'asc' | 'desc'
 * maxHeight?: string
 */
const TerminalTable = ({
  columns = [],
  data = [],
  onRowClick,
  defaultSort,
  defaultDir = 'desc',
  maxHeight = 'none',
  emptyMessage = 'No data available',
}) => {
  const [sortKey, setSortKey] = React.useState(defaultSort || null);
  const [sortDir, setSortDir] = React.useState(defaultDir);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = React.useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      const an = parseFloat(av);
      const bn = parseFloat(bv);
      const cmp = !isNaN(an) && !isNaN(bn)
        ? an - bn
        : String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  // Build grid-template-columns
  const gridCols = [
    ...columns.map(c => c.width
      ? (typeof c.width === 'number' ? `${c.width}px` : c.width)
      : '1fr'
    ),
    ...(onRowClick ? ['28px'] : []),
  ].join(' ');

  return (
    <div style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div
        className="terminal-header"
        style={{ gridTemplateColumns: gridCols, padding: '6px 12px' }}
      >
        {columns.map(col => (
          <span
            key={col.key}
            onClick={col.sortable !== false ? () => handleSort(col.key) : undefined}
            style={{
              justifyContent: col.align === 'right' ? 'flex-end' : col.align === 'center' ? 'center' : 'flex-start',
              cursor: col.sortable !== false ? 'pointer' : 'default',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              userSelect: 'none',
            }}
          >
            {col.label}
            {sortKey === col.key && (
              sortDir === 'asc'
                ? <ChevronUp size={9} style={{ color: 'var(--green)' }} />
                : <ChevronDown size={9} style={{ color: 'var(--green)' }} />
            )}
            {sortKey !== col.key && col.sortable !== false && (
              <ChevronDown size={9} style={{ opacity: 0.2 }} />
            )}
          </span>
        ))}
        {onRowClick && <span />}
      </div>

      {/* Body */}
      <div style={{ overflowY: 'auto', maxHeight }}>
        {sorted.length === 0 ? (
          <div style={{
            padding: '32px 12px',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '12px',
          }}>
            {emptyMessage}
          </div>
        ) : (
          sorted.map((row, i) => (
            <div
              key={i}
              className="terminal-row"
              style={{
                gridTemplateColumns: gridCols,
                padding: '7px 12px',
                cursor: onRowClick ? 'pointer' : 'default',
              }}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map(col => {
                const val = row[col.key];
                const cell = col.render ? col.render(val, row) : val;
                return (
                  <div
                    key={col.key}
                    style={{
                      textAlign: col.align || 'left',
                      fontSize: '12px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {cell ?? '—'}
                  </div>
                );
              })}
              {onRowClick && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span className="row-arrow">›</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TerminalTable;
