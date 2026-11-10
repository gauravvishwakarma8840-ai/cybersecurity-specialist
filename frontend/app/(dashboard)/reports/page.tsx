'use client';

import { useEffect, useState } from 'react';
import { reportsApi, type Report } from '@/lib/api';

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ title: '', report_type: 'executive_summary' });
  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<Report | null>(null);

  useEffect(() => { loadReports(); }, []);

  async function loadReports() {
    setLoading(true);
    try { const r = await reportsApi.list(); setReports(r); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault(); setGenerating(true);
    try {
      const r = await reportsApi.create({ title: form.title, report_type: form.report_type });
      setReports(prev => [r, ...prev]);
      setShowForm(false);
      setSelected(r);
    } catch (err) { console.error(err); }
    finally { setGenerating(false); }
  };

  return (
    <div style={{ display: 'flex', gap: 24 }}>
      {/* Report List */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Generated Reports</h3>
          <button className="btn btn--primary btn--sm" onClick={() => setShowForm(true)}>+ New Report</button>
        </div>

        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 80, borderRadius: 10 }} />
          ))
        ) : reports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--color-text-muted)' }}>
            <div style={{ fontSize: '2rem', marginBottom: 12 }}>📊</div>
            <p>No reports generated yet. Create your first security report.</p>
          </div>
        ) : (
          reports.map(r => (
            <button
              key={r.id}
              className="card"
              style={{ textAlign: 'left', cursor: 'pointer', transition: 'all 0.2s', border: selected?.id === r.id ? '1px solid rgba(0,212,255,0.4)' : undefined }}
              onClick={() => setSelected(r)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>{r.title}</h4>
                  <p style={{ margin: '4px 0 8px', fontSize: '0.8rem' }}>{r.report_type.replace(/_/g, ' ')}</p>
                </div>
                <span className={`badge badge--${r.status === 'completed' ? 'success' : r.status === 'failed' ? 'critical' : 'medium'}`}>
                  {r.status}
                </span>
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                Generated: {new Date(r.created_at).toLocaleString()}
              </span>
            </button>
          ))
        )}
      </div>

      {/* Report Detail */}
      {selected && (
        <div className="card" style={{ width: 420, height: 'fit-content', position: 'sticky', top: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{selected.title}</h3>
            <button className="btn btn--icon btn--secondary" onClick={() => setSelected(null)}>✕</button>
          </div>
          {selected.content ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {Object.entries(selected.content.sections as Record<string, Record<string, unknown>> || {}).map(([section, data]) => (
                <div key={section} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--color-border)', borderRadius: 8, padding: 14 }}>
                  <h4 style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-cyan)', marginBottom: 10 }}>{section.replace(/_/g, ' ')}</h4>
                  {Object.entries(data as Record<string, unknown>).map(([key, value]) => (
                    <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>{key.replace(/_/g, ' ')}</span>
                      <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{String(value)}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted text-sm">Report content not available.</p>
          )}
        </div>
      )}

      {/* Generate Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 24, borderBottom: '1px solid var(--color-border)' }}>
              <h3>Generate Security Report</h3>
              <button className="btn btn--icon btn--secondary" onClick={() => setShowForm(false)}>✕</button>
            </div>
            <form onSubmit={handleGenerate} style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Report Title</label>
                <input className="form-input" placeholder="Q3 2026 Security Assessment" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label className="form-label">Report Type</label>
                <select className="form-input" value={form.report_type} onChange={e => setForm(f => ({ ...f, report_type: e.target.value }))}>
                  {['executive_summary', 'threat_intelligence', 'vulnerability_assessment', 'incident_report', 'compliance', 'custom'].map(t =>
                    <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                  )}
                </select>
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn--secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={generating}>{generating ? '⟳ Generating...' : 'Generate Report'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
