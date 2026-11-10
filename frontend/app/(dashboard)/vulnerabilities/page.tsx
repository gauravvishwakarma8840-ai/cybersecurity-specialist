'use client';

import { useEffect, useState, useCallback } from 'react';
import { vulnsApi, type Vulnerability } from '@/lib/api';

function CvssBar({ score }: { score: number }) {
  const color = score >= 9 ? 'var(--color-critical)' : score >= 7 ? 'var(--color-high)' : score >= 4 ? 'var(--color-medium)' : 'var(--color-success)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ width: 80, height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3 }}>
        <div style={{ height: '100%', width: `${(score / 10) * 100}%`, background: color, borderRadius: 3 }} />
      </div>
      <span style={{ color, fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>{score.toFixed(1)}</span>
    </div>
  );
}

export default function VulnerabilitiesPage() {
  const [vulns, setVulns] = useState<Vulnerability[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('');
  const [selected, setSelected] = useState<Vulnerability | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await vulnsApi.list({ page, severity: severityFilter || undefined });
      setVulns(res.items); setTotal(res.total);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [page, severityFilter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {['', 'critical', 'high', 'medium', 'low'].map(s => (
            <button
              key={s}
              className={`btn btn--sm ${severityFilter === s ? 'btn--primary' : 'btn--secondary'}`}
              onClick={() => setSeverityFilter(s)}
            >
              {s === '' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <span className="text-muted text-sm">{total} vulnerabilities</span>
      </div>

      <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th>CVE ID</th><th>Title</th><th>CVSS Score</th><th>Severity</th>
              <th>Status</th><th>Patch</th><th>Exploit</th><th>Discovered</th>
            </tr>
          </thead>
          <tbody>
            {loading ? Array.from({ length: 8 }).map((_, i) => (
              <tr key={i}>{Array.from({ length: 8 }).map((_, j) => <td key={j}><div className="skeleton" style={{ height: 18 }} /></td>)}</tr>
            )) : vulns.length === 0 ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-muted)' }}>No vulnerabilities tracked. Add CVEs to monitor your exposure.</td></tr>
            ) : (
              vulns.map(v => (
                <tr key={v.id} style={{ cursor: 'pointer' }} onClick={() => setSelected(v)}>
                  <td>{v.cve_id ? <a href={`https://nvd.nist.gov/vuln/detail/${v.cve_id}`} target="_blank" rel="noopener noreferrer" className="font-mono" style={{ color: 'var(--color-cyan)', fontSize: '0.83rem' }} onClick={e => e.stopPropagation()}>{v.cve_id}</a> : <span className="text-muted">—</span>}</td>
                  <td style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.875rem' }}>{v.title}</td>
                  <td><CvssBar score={v.cvss_score} /></td>
                  <td><span className={`badge badge--${v.severity}`}>{v.severity}</span></td>
                  <td><span className={`badge badge--${v.status === 'open' ? 'critical' : v.status === 'mitigated' ? 'success' : 'medium'}`}>{v.status.replace('_', ' ')}</span></td>
                  <td>{v.patch_available ? <span style={{ color: 'var(--color-success)' }}>✓ Available</span> : <span className="text-muted">✗ None</span>}</td>
                  <td>{v.exploit_available ? <span style={{ color: 'var(--color-critical)', fontWeight: 700 }}>⚠ Yes</span> : <span className="text-muted">No</span>}</td>
                  <td className="text-sm text-muted">{new Date(v.discovered_at).toLocaleDateString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: 24, borderBottom: '1px solid var(--color-border)' }}>
              <div>
                {selected.cve_id && <span className="badge badge--cyan font-mono">{selected.cve_id}</span>}
                <h3 style={{ marginTop: 8 }}>{selected.title}</h3>
              </div>
              <button className="btn btn--icon btn--secondary" onClick={() => setSelected(null)}>✕</button>
            </div>
            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <p>{selected.description}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--color-border)', borderRadius: 10, padding: 16 }}>
                {[
                  ['CVSS Score', selected.cvss_score.toFixed(1)],
                  ['Severity', selected.severity.toUpperCase()],
                  ['Status', selected.status.replace('_', ' ')],
                  ['Affected Software', selected.affected_software || '—'],
                  ['Patch Available', selected.patch_available ? 'Yes' : 'No'],
                  ['Exploit Available', selected.exploit_available ? 'YES (Critical!)' : 'No'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
                    <p style={{ margin: '4px 0 0', fontWeight: 500 }}>{value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
