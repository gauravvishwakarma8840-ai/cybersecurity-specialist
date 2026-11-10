'use client';

import { useEffect, useState, useCallback } from 'react';
import { assetsApi, type Asset } from '@/lib/api';

function RiskScore({ score }: { score: number }) {
  const color = score > 70 ? 'var(--color-critical)' : score > 40 ? 'var(--color-medium)' : 'var(--color-success)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <svg width="32" height="32" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
        <circle cx="18" cy="18" r="15.9" fill="none" stroke={color} strokeWidth="3"
          strokeDasharray={`${score} ${100 - score}`} strokeDashoffset="25" strokeLinecap="round" />
      </svg>
      <span style={{ color, fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: '0.875rem' }}>{score.toFixed(0)}</span>
    </div>
  );
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [assetType, setAssetType] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ hostname: '', ip_address: '', os_type: '', asset_type: 'server', owner: '', department: '' });
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await assetsApi.list({ page, search, asset_type: assetType || undefined });
      setAssets(res.items); setTotal(res.total);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [page, search, assetType]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault(); setAdding(true);
    try {
      await assetsApi.create(form);
      setShowAdd(false); setForm({ hostname: '', ip_address: '', os_type: '', asset_type: 'server', owner: '', department: '' });
      load();
    } catch (err) { console.error(err); }
    finally { setAdding(false); }
  };

  const ASSET_ICONS: Record<string, string> = {
    server: '🖥️', workstation: '💻', network_device: '🔌', cloud_instance: '☁️', container: '📦', iot: '📡', other: '📱',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <input className="form-input" style={{ width: 240 }} placeholder="Search hostnames..." value={search} onChange={e => setSearch(e.target.value)} />
          <select className="form-input" value={assetType} onChange={e => setAssetType(e.target.value)}>
            <option value="">All Types</option>
            {['server', 'workstation', 'network_device', 'cloud_instance', 'container', 'iot'].map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
          </select>
        </div>
        <button className="btn btn--primary btn--sm" onClick={() => setShowAdd(true)}>+ Add Asset</button>
      </div>

      <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr><th>Asset</th><th>IP Address</th><th>OS</th><th>Type</th><th>Owner</th><th>Internet Facing</th><th>Risk Score</th><th>Last Seen</th></tr>
          </thead>
          <tbody>
            {loading ? Array.from({ length: 8 }).map((_, i) => (
              <tr key={i}>{Array.from({ length: 8 }).map((_, j) => <td key={j}><div className="skeleton" style={{ height: 18 }} /></td>)}</tr>
            )) : assets.length === 0 ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-muted)' }}>No assets tracked. Add your first asset.</td></tr>
            ) : (
              assets.map(a => (
                <tr key={a.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: '1.1rem' }}>{ASSET_ICONS[a.asset_type] || '📱'}</span>
                      <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', fontSize: '0.875rem' }}>{a.hostname}</span>
                    </div>
                  </td>
                  <td><span className="font-mono" style={{ fontSize: '0.83rem' }}>{a.ip_address || '—'}</span></td>
                  <td className="text-sm text-muted">{a.os_type || '—'}</td>
                  <td><span className="badge badge--info">{a.asset_type.replace('_', ' ')}</span></td>
                  <td className="text-sm">{a.owner || '—'}</td>
                  <td>
                    {a.is_internet_facing
                      ? <span style={{ color: 'var(--color-critical)', fontWeight: 700 }}>⚠ Yes</span>
                      : <span className="text-muted">No</span>
                    }
                  </td>
                  <td><RiskScore score={a.risk_score} /></td>
                  <td className="text-sm text-muted">{new Date(a.last_seen).toLocaleDateString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 24, borderBottom: '1px solid var(--color-border)' }}>
              <h3>Add Asset</h3>
              <button className="btn btn--icon btn--secondary" onClick={() => setShowAdd(false)}>✕</button>
            </div>
            <form onSubmit={handleAdd} style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">Hostname</label>
                  <input className="form-input" placeholder="web-server-01" value={form.hostname} onChange={e => setForm(f => ({ ...f, hostname: e.target.value }))} required />
                </div>
                <div className="form-group">
                  <label className="form-label">IP Address</label>
                  <input className="form-input" placeholder="192.168.1.10" value={form.ip_address} onChange={e => setForm(f => ({ ...f, ip_address: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">OS Type</label>
                  <input className="form-input" placeholder="Ubuntu Linux" value={form.os_type} onChange={e => setForm(f => ({ ...f, os_type: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Asset Type</label>
                  <select className="form-input" value={form.asset_type} onChange={e => setForm(f => ({ ...f, asset_type: e.target.value }))}>
                    {['server', 'workstation', 'network_device', 'cloud_instance', 'container', 'iot', 'other'].map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Owner</label>
                  <input className="form-input" placeholder="IT Department" value={form.owner} onChange={e => setForm(f => ({ ...f, owner: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Department</label>
                  <input className="form-input" placeholder="Engineering" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn--secondary" onClick={() => setShowAdd(false)}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={adding}>{adding ? 'Adding...' : 'Add Asset'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
