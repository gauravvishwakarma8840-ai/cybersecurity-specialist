'use client';

import { useEffect, useState, useCallback } from 'react';
import { threatsApi, type ThreatIndicator } from '@/lib/api';

export default function ThreatsPage() {
  const [threats, setThreats] = useState<ThreatIndicator[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ indicator_type: 'ip', value: '', threat_type: 'unknown', confidence_score: '0.5' });
  const [adding, setAdding] = useState(false);

  const totalPages = Math.ceil(total / 25);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await threatsApi.list({ page, search });
      setThreats(res.items); setTotal(res.total);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [page, search]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault(); setAdding(true);
    try {
      await threatsApi.create({ ...form, confidence_score: parseFloat(form.confidence_score) });
      setShowAdd(false); load();
    } catch (err) { console.error(err); }
    finally { setAdding(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <input
          className="form-input"
          style={{ width: 320 }}
          placeholder="Search IOCs..."
          value={search}
          onChange={e => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <button className="btn btn--primary btn--sm" onClick={() => setShowAdd(true)}>+ Add IOC</button>
      </div>

      <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th>Type</th><th>Value</th><th>Threat Type</th><th>Confidence</th>
              <th>Abuse Score</th><th>Country</th><th>Source</th><th>Last Seen</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? Array.from({ length: 8 }).map((_, i) => (
              <tr key={i}>{Array.from({ length: 9 }).map((_, j) => <td key={j}><div className="skeleton" style={{ height: 18 }} /></td>)}</tr>
            )) : threats.length === 0 ? (
              <tr><td colSpan={9} style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-muted)' }}>No threat indicators yet. Add IOCs to start tracking.</td></tr>
            ) : (
              threats.map(t => (
                <tr key={t.id}>
                  <td><span className="badge badge--cyan">{t.indicator_type}</span></td>
                  <td><span className="font-mono" style={{ fontSize: '0.8rem' }}>{t.value}</span></td>
                  <td><span className="badge badge--medium">{t.threat_type}</span></td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 60, height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2 }}>
                        <div style={{ height: '100%', width: `${t.confidence_score * 100}%`, background: t.confidence_score > 0.7 ? 'var(--color-critical)' : 'var(--color-medium)', borderRadius: 2 }} />
                      </div>
                      <span className="text-sm">{(t.confidence_score * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td>
                    {t.abuse_confidence > 0
                      ? <span style={{ color: t.abuse_confidence > 50 ? 'var(--color-critical)' : 'var(--color-medium)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{t.abuse_confidence}</span>
                      : <span className="text-muted">—</span>
                    }
                  </td>
                  <td>{t.country_code ? <span className="badge badge--info">{t.country_code}</span> : <span className="text-muted">—</span>}</td>
                  <td className="text-sm text-muted">{t.source}</td>
                  <td className="text-sm text-muted">{new Date(t.last_seen).toLocaleDateString()}</td>
                  <td><span className={`badge badge--${t.is_active ? 'critical' : 'success'}`}>{t.is_active ? 'Active' : 'Inactive'}</span></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16, marginTop: 8 }}>
          <button className="btn btn--secondary btn--sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Previous</button>
          <span className="text-sm text-muted">Page {page} of {totalPages}</span>
          <button className="btn btn--secondary btn--sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      )}

      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 24, borderBottom: '1px solid var(--color-border)' }}>
              <h3>Add Threat Indicator</h3>
              <button className="btn btn--icon btn--secondary" onClick={() => setShowAdd(false)}>✕</button>
            </div>
            <form onSubmit={handleAdd} style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Indicator Type</label>
                <select className="form-input" value={form.indicator_type} onChange={e => setForm(f => ({ ...f, indicator_type: e.target.value }))}>
                  {['ip', 'domain', 'url', 'hash_md5', 'hash_sha1', 'hash_sha256', 'email'].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Value</label>
                <input className="form-input" placeholder="e.g. 192.168.1.100 or evil.com" value={form.value} onChange={e => setForm(f => ({ ...f, value: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label className="form-label">Threat Type</label>
                <select className="form-input" value={form.threat_type} onChange={e => setForm(f => ({ ...f, threat_type: e.target.value }))}>
                  {['malware', 'phishing', 'c2', 'scanner', 'botnet', 'ransomware', 'apt', 'spam', 'exploit', 'unknown'].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn--secondary" onClick={() => setShowAdd(false)}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={adding}>{adding ? 'Adding...' : 'Add & Enrich'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
