'use client';

import { useEffect, useState, useCallback } from 'react';
import { alertsApi, type Alert } from '@/lib/api';
import styles from './page.module.css';

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];

function SeverityBadge({ severity }: { severity: string }) {
  return <span className={`badge badge--${severity}`}>{severity}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    open: 'critical', investigating: 'medium', resolved: 'success', false_positive: 'info',
  };
  return <span className={`badge badge--${map[status] || 'info'}`}>{status.replace('_', ' ')}</span>;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ severity: '', status: '', search: '' });
  const [selected, setSelected] = useState<Alert | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await alertsApi.list({ page, page_size: 20, ...filters });
      setAlerts(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => { load(); }, [load]);

  const handleStatusUpdate = async (id: string, status: Alert['status']) => {
    try {
      await alertsApi.update(id, { status });
      load();
      setSelected(null);
    } catch (e) { console.error(e); }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className={styles.page}>
      {/* Filters */}
      <div className={styles.toolbar}>
        <div className={styles.filters}>
          <input
            className="form-input"
            style={{ width: 260 }}
            placeholder="Search alerts..."
            value={filters.search}
            onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
          />
          <select
            className="form-input"
            value={filters.severity}
            onChange={e => setFilters(f => ({ ...f, severity: e.target.value }))}
          >
            <option value="">All Severities</option>
            {SEVERITY_ORDER.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
          </select>
          <select
            className="form-input"
            value={filters.status}
            onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
          >
            <option value="">All Statuses</option>
            {['open', 'investigating', 'resolved', 'false_positive'].map(s =>
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            )}
          </select>
        </div>
        <div className={styles.summary}>
          <span className="text-muted text-sm">{total.toLocaleString()} alerts total</span>
        </div>
      </div>

      {/* Table */}
      <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Title</th>
              <th>Type</th>
              <th>Source IP</th>
              <th>MITRE</th>
              <th>Status</th>
              <th>Risk</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 9 }).map((_, j) => (
                    <td key={j}><div className="skeleton" style={{ height: 20, borderRadius: 4 }} /></td>
                  ))}
                </tr>
              ))
            ) : alerts.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-muted)' }}>
                  No alerts found. Create one or adjust filters.
                </td>
              </tr>
            ) : (
              alerts.map(alert => (
                <tr key={alert.id} className={styles.tableRow} onClick={() => setSelected(alert)}>
                  <td><SeverityBadge severity={alert.severity} /></td>
                  <td>
                    <div className={styles.alertTitle}>{alert.title}</div>
                    {alert.ai_summary && <div className={styles.aiSummary}>🤖 {alert.ai_summary.slice(0, 80)}...</div>}
                  </td>
                  <td><span className="font-mono" style={{ fontSize: '0.78rem' }}>{alert.alert_type}</span></td>
                  <td>
                    {alert.source_ip
                      ? <span className="font-mono" style={{ fontSize: '0.8rem' }}>{alert.source_ip}</span>
                      : <span className="text-muted">—</span>
                    }
                  </td>
                  <td>
                    {alert.mitre_technique
                      ? <span className={styles.mitreTag}>{alert.mitre_technique}</span>
                      : <span className="text-muted">—</span>
                    }
                  </td>
                  <td><StatusBadge status={alert.status} /></td>
                  <td>
                    <div className={styles.riskBar}>
                      <div
                        className={styles.riskFill}
                        style={{
                          width: `${alert.risk_score}%`,
                          background: alert.risk_score > 70 ? 'var(--color-critical)' : alert.risk_score > 40 ? 'var(--color-medium)' : 'var(--color-success)',
                        }}
                      />
                      <span>{alert.risk_score.toFixed(0)}</span>
                    </div>
                  </td>
                  <td className="text-muted text-sm">
                    {new Date(alert.created_at).toLocaleDateString()}
                  </td>
                  <td onClick={e => e.stopPropagation()}>
                    {alert.status === 'open' && (
                      <div className={styles.actionBtns}>
                        <button className="btn btn--sm btn--secondary" onClick={() => handleStatusUpdate(alert.id, 'investigating')}>
                          Investigate
                        </button>
                        <button className="btn btn--sm btn--secondary" onClick={() => handleStatusUpdate(alert.id, 'resolved')}>
                          Resolve
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button className="btn btn--secondary btn--sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Previous</button>
          <span className="text-sm text-muted">Page {page} of {totalPages}</span>
          <button className="btn btn--secondary btn--sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      )}

      {/* Detail Modal */}
      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div>
                <SeverityBadge severity={selected.severity} />
                <h3 style={{ marginTop: 8 }}>{selected.title}</h3>
              </div>
              <button className="btn btn--icon btn--secondary" onClick={() => setSelected(null)}>✕</button>
            </div>
            <div className={styles.modalBody}>
              <p>{selected.description}</p>
              <div className={styles.detailGrid}>
                <div><span className="text-muted text-sm">Type</span><p className="font-mono">{selected.alert_type}</p></div>
                <div><span className="text-muted text-sm">Status</span><StatusBadge status={selected.status} /></div>
                <div><span className="text-muted text-sm">Source IP</span><p className="font-mono">{selected.source_ip || '—'}</p></div>
                <div><span className="text-muted text-sm">Dest IP</span><p className="font-mono">{selected.dest_ip || '—'}</p></div>
                <div><span className="text-muted text-sm">MITRE Tactic</span><p>{selected.mitre_tactic || '—'}</p></div>
                <div><span className="text-muted text-sm">MITRE Technique</span><p>{selected.mitre_technique || '—'}</p></div>
                <div><span className="text-muted text-sm">Risk Score</span><p style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-critical)' }}>{selected.risk_score}</p></div>
                <div><span className="text-muted text-sm">Created</span><p>{new Date(selected.created_at).toLocaleString()}</p></div>
              </div>
              {selected.ai_summary && (
                <div className={styles.aiPanel}>
                  <div className={styles.aiPanelHeader}>🤖 AI Analysis</div>
                  <p>{selected.ai_summary}</p>
                </div>
              )}
              <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                {selected.status === 'open' && (
                  <>
                    <button className="btn btn--secondary" onClick={() => handleStatusUpdate(selected.id, 'investigating')}>Mark as Investigating</button>
                    <button className="btn btn--primary" onClick={() => handleStatusUpdate(selected.id, 'resolved')}>Mark as Resolved</button>
                    <button className="btn btn--secondary" onClick={() => handleStatusUpdate(selected.id, 'false_positive')}>False Positive</button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
