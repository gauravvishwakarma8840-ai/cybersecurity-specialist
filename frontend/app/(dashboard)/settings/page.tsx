'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { settingsApi } from '@/lib/api';

interface TeamMember {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active?: boolean;
  last_login?: string | null;
}

export default function SettingsPage() {
  const { user, organization } = useAuth();
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [rotating, setRotating] = useState(false);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' });
  const [pwMsg, setPwMsg] = useState('');
  const [activeTab, setActiveTab] = useState<'org' | 'security' | 'team' | 'api'>('org');

  // Add Member Modal State
  const [showAddMember, setShowAddMember] = useState(false);
  const [memberForm, setMemberForm] = useState({
    full_name: '',
    email: '',
    role: 'analyst',
    password: '',
  });
  const [memberError, setMemberError] = useState('');
  const [addingMember, setAddingMember] = useState(false);

  const reloadTeam = async () => {
    try {
      const data = await settingsApi.getTeam();
      setTeam(data as TeamMember[]);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    reloadTeam();
  }, []);

  const handleRotateKey = async () => {
    setRotating(true);
    try {
      const res = await settingsApi.rotateApiKey();
      setApiKey(res.api_key);
    } catch (e) {
      console.error(e);
    } finally {
      setRotating(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.new !== passwords.confirm) {
      setPwMsg('Passwords do not match.');
      return;
    }
    try {
      await settingsApi.changePassword(passwords.current, passwords.new);
      setPwMsg('Password changed successfully.');
      setPasswords({ current: '', new: '', confirm: '' });
    } catch (err: unknown) {
      setPwMsg(err instanceof Error ? err.message : 'Failed to change password.');
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    setMemberError('');
    setAddingMember(true);
    try {
      await settingsApi.addTeamMember(memberForm);
      setShowAddMember(false);
      setMemberForm({ full_name: '', email: '', role: 'analyst', password: '' });
      await reloadTeam();
    } catch (err: unknown) {
      setMemberError(err instanceof Error ? err.message : 'Failed to add member.');
    } finally {
      setAddingMember(false);
    }
  };

  const handleRoleChange = async (memberId: string, newRole: string) => {
    try {
      await settingsApi.updateMemberRole(memberId, newRole);
      await reloadTeam();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to update role.');
    }
  };

  const handleStatusToggle = async (memberId: string, currentStatus: boolean) => {
    try {
      await settingsApi.updateMemberStatus(memberId, !currentStatus);
      await reloadTeam();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to update status.');
    }
  };

  const isAdmin = user?.role === 'admin';

  const TABS = [
    { id: 'org', label: '🏢 Organization' },
    { id: 'security', label: '🔐 Security' },
    { id: 'team', label: '👥 Team' },
    { id: 'api', label: '🔑 API Keys' },
  ] as const;

  return (
    <div style={{ maxWidth: 880, display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid var(--color-border)', paddingBottom: 12 }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`btn btn--sm ${activeTab === tab.id ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Organization Tab */}
      {activeTab === 'org' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Organization Details</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
            {[
              ['Organization Name', organization?.name || '—'],
              ['Slug / Identifier', organization?.slug || '—'],
              ['Current Plan', organization?.plan?.toUpperCase() || '—'],
              ['Status', organization?.is_active ? '✓ Active' : '✗ Inactive'],
              ['Created', organization?.created_at ? new Date(organization.created_at).toLocaleDateString() : '—'],
              ['Member Since', user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'],
            ].map(([label, value]) => (
              <div key={label} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--color-border)', borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>{label}</div>
                <div style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', fontSize: '0.875rem' }}>{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Change Password</h3>
          <form onSubmit={handlePasswordChange} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Current Password</label>
              <input type="password" className="form-input" style={{ maxWidth: 360 }} value={passwords.current} onChange={e => setPasswords(p => ({ ...p, current: e.target.value }))} required />
            </div>
            <div className="form-group">
              <label className="form-label">New Password (min. 12 chars)</label>
              <input type="password" className="form-input" style={{ maxWidth: 360 }} value={passwords.new} onChange={e => setPasswords(p => ({ ...p, new: e.target.value }))} required minLength={12} />
            </div>
            <div className="form-group">
              <label className="form-label">Confirm New Password</label>
              <input type="password" className="form-input" style={{ maxWidth: 360 }} value={passwords.confirm} onChange={e => setPasswords(p => ({ ...p, confirm: e.target.value }))} required />
            </div>
            {pwMsg && <p style={{ color: pwMsg.includes('success') ? 'var(--color-success)' : 'var(--color-critical)', fontSize: '0.875rem' }}>{pwMsg}</p>}
            <button type="submit" className="btn btn--primary" style={{ width: 'fit-content' }}>Update Password</button>
          </form>
        </div>
      )}

      {/* Team Tab */}
      {activeTab === 'team' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Team Members ({team.length})</h3>
            {isAdmin && (
              <button className="btn btn--primary btn--sm" onClick={() => setShowAddMember(true)}>
                + Add Member
              </button>
            )}
          </div>

          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  {isAdmin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {team.map(m => {
                  const isActive = m.is_active !== false;
                  const isSelf = user?.email === m.email;

                  return (
                    <tr key={m.id}>
                      <td style={{ fontWeight: 600 }}>
                        {m.full_name} {isSelf && <span style={{ color: 'var(--color-cyan)', fontSize: '0.75rem' }}>(You)</span>}
                      </td>
                      <td className="font-mono" style={{ fontSize: '0.875rem' }}>{m.email}</td>
                      <td>
                        {isAdmin && !isSelf ? (
                          <select
                            className="form-input"
                            style={{ padding: '3px 8px', fontSize: '0.78rem', width: 'auto' }}
                            value={m.role}
                            onChange={(e) => handleRoleChange(m.id, e.target.value)}
                          >
                            <option value="admin">admin</option>
                            <option value="analyst">analyst</option>
                            <option value="viewer">viewer</option>
                          </select>
                        ) : (
                          <span className={`badge badge--${m.role === 'admin' ? 'critical' : m.role === 'analyst' ? 'medium' : 'info'}`}>
                            {m.role}
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={`badge badge--${isActive ? 'success' : 'danger'}`}>
                          {isActive ? 'Active' : 'Deactivated'}
                        </span>
                      </td>
                      {isAdmin && (
                        <td>
                          {!isSelf && (
                            <button
                              className={`btn btn--sm ${isActive ? 'btn--secondary' : 'btn--primary'}`}
                              style={{ padding: '3px 8px', fontSize: '0.75rem' }}
                              onClick={() => handleStatusToggle(m.id, isActive)}
                            >
                              {isActive ? 'Deactivate' : 'Activate'}
                            </button>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Add Team Member Modal */}
          {showAddMember && (
            <div className="modal-overlay" onClick={() => setShowAddMember(false)}>
              <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 440 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: 20, borderBottom: '1px solid var(--color-border)' }}>
                  <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Add Team Member</h3>
                  <button className="btn btn--icon btn--secondary" onClick={() => setShowAddMember(false)}>✕</button>
                </div>
                <form onSubmit={handleAddMember} style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {memberError && <div style={{ color: 'var(--color-critical)', fontSize: '0.85rem' }}>{memberError}</div>}
                  <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input
                      className="form-input"
                      placeholder="e.g. Alice Smith"
                      value={memberForm.full_name}
                      onChange={(e) => setMemberForm({ ...memberForm, full_name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email Address</label>
                    <input
                      type="email"
                      className="form-input"
                      placeholder="alice@company.com"
                      value={memberForm.email}
                      onChange={(e) => setMemberForm({ ...memberForm, email: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Role</label>
                    <select
                      className="form-input"
                      value={memberForm.role}
                      onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                    >
                      <option value="analyst">Analyst (SOC operations, alerts, threats)</option>
                      <option value="admin">Admin (Full organization control)</option>
                      <option value="viewer">Viewer (Read-only access)</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Initial Password (min. 12 chars)</label>
                    <input
                      type="password"
                      className="form-input"
                      value={memberForm.password}
                      onChange={(e) => setMemberForm({ ...memberForm, password: e.target.value })}
                      required
                      minLength={12}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 10 }}>
                    <button type="button" className="btn btn--secondary" onClick={() => setShowAddMember(false)}>
                      Cancel
                    </button>
                    <button type="submit" className="btn btn--primary" disabled={addingMember}>
                      {addingMember ? 'Adding...' : 'Add Member'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* API Keys Tab */}
      {activeTab === 'api' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>API Key Management</h3>
          <p className="text-sm text-muted">Use your organization API key to programmatically ingest logs via the REST API or CLI log forwarders. Keys are stored as bcrypt hashes — shown only once on generation.</p>

          {apiKey ? (
            <div>
              <div className="form-label" style={{ marginBottom: 8 }}>Your New API Key (copy now — won&apos;t be shown again)</div>
              <div className="code-block" style={{ userSelect: 'all', fontSize: '0.8rem', wordBreak: 'break-all' }}>{apiKey}</div>
              <button className="btn btn--secondary btn--sm" style={{ marginTop: 10 }} onClick={() => { navigator.clipboard.writeText(apiKey); }}>
                📋 Copy to Clipboard
              </button>
            </div>
          ) : (
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--color-border)', borderRadius: 10, padding: 20 }}>
              <p style={{ fontSize: '0.875rem', marginBottom: 16 }}>No API key currently displayed. Generate a new key to authenticate API requests.</p>
              <button className="btn btn--primary btn--sm" onClick={handleRotateKey} disabled={rotating}>
                {rotating ? '⟳ Generating...' : '🔑 Generate New API Key'}
              </button>
            </div>
          )}

          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 16 }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 10 }}>Example: Ingest a log via API Key</h4>
            <div className="code-block">
{`# Authenticate with X-API-Key header (recommended for SIEM/agents):
curl -X POST http://localhost:8000/api/v1/logs/ingest \\
  -H "X-API-Key: cs_your_api_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "source": "firewall-01",
    "raw_log": "Jul 30 12:00:00 server sshd[1234]: Failed password for root from 192.168.1.100 port 22 ssh2",
    "log_type": "auth"
  }'`}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
