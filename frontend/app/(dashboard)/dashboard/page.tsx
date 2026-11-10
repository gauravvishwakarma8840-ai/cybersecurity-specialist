'use client';

import { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { dashboardApi, type DashboardStats, type AlertTrend, type ThreatDistribution } from '@/lib/api';
import styles from './page.module.css';

const SEVERITY_COLORS = {
  critical: '#FF3B3B', high: '#FF6B35', medium: '#FFA500', low: '#00C896',
};

const THREAT_COLORS = ['#FF3B3B', '#FF6B35', '#FFA500', '#00C896', '#00D4FF', '#6B8DB2', '#A855F7', '#EC4899'];

interface StatCardItem {
  key: keyof DashboardStats;
  label: string;
  accent: string;
  icon: string;
  isFloat?: boolean;
}

const STAT_CARDS: StatCardItem[] = [
  { key: 'open_alerts',           label: 'Open Alerts',        accent: '#FF3B3B', icon: '🚨' },
  { key: 'critical_alerts',       label: 'Critical Alerts',    accent: '#FF3B3B', icon: '⚠️' },
  { key: 'total_threats',         label: 'Active Threats',     accent: '#FFA500', icon: '🕵️' },
  { key: 'open_vulnerabilities',  label: 'Open Vulns',         accent: '#FF6B35', icon: '🛡️' },
  { key: 'total_assets',          label: 'Total Assets',       accent: '#00D4FF', icon: '🖥️' },
  { key: 'logs_last_24h',         label: 'Logs (24h)',         accent: '#00C896', icon: '📋' },
  { key: 'flagged_logs',          label: 'Flagged Logs',       accent: '#FFA500', icon: '🚩' },
  { key: 'risk_score_avg',        label: 'Avg Risk Score',     accent: '#A855F7', icon: '📊', isFloat: true },
];

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { color: string; name: string; value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className={styles.chartTooltip}>
      <p className={styles.tooltipLabel}>{label}</p>
      {payload.map(p => (
        <div key={p.name} className={styles.tooltipItem} style={{ color: p.color }}>
          <span>{p.name}</span>
          <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trends, setTrends] = useState<AlertTrend[]>([]);
  const [distribution, setDistribution] = useState<ThreatDistribution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, t, d] = await Promise.all([
          dashboardApi.getStats(),
          dashboardApi.getAlertTrends(7),
          dashboardApi.getThreatDistribution(),
        ]);
        setStats(s);
        setTrends(t);
        setDistribution(d);
      } catch (err) {
        console.error('Dashboard load error:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
    // Auto-refresh every 30 seconds
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={styles.page}>
      {/* KPI Cards */}
      <div className={styles.statsGrid}>
        {STAT_CARDS.map(card => (
          <div key={card.key} className="stat-card" style={{ '--accent-color': card.accent } as React.CSSProperties}>
            <div className="stat-card__icon" style={{ background: `${card.accent}1A`, border: `1px solid ${card.accent}33` }}>
              <span style={{ fontSize: '1.25rem' }}>{card.icon}</span>
            </div>
            {loading ? (
              <div className="skeleton" style={{ height: 36, borderRadius: 8, marginBottom: 4 }} />
            ) : (
              <div className="stat-card__value" style={{ color: card.accent }}>
                {card.isFloat
                  ? ((stats?.[card.key] as number) ?? 0).toFixed(1)
                  : (stats?.[card.key] as number ?? 0).toLocaleString()
                }
              </div>
            )}
            <div className="stat-card__label">{card.label}</div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className={styles.chartsRow}>
        {/* Alert Trend Chart */}
        <div className={`card ${styles.chartCard}`}>
          <div className={styles.chartHeader}>
            <h3>Alert Trends (7 Days)</h3>
            <span className="badge badge--cyan">Live</span>
          </div>
          {loading || !trends.length ? (
            <div className={styles.chartPlaceholder}>
              <div className="skeleton" style={{ height: '100%', borderRadius: 8 }} />
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  {Object.entries(SEVERITY_COLORS).map(([key, color]) => (
                    <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={color} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <XAxis dataKey="date" tick={{ fill: '#4B5563', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#4B5563', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#94A3B8' }} />
                {Object.entries(SEVERITY_COLORS).map(([key, color]) => (
                  <Area
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={color}
                    fill={`url(#grad-${key})`}
                    strokeWidth={2}
                    dot={false}
                    name={key.charAt(0).toUpperCase() + key.slice(1)}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Threat Distribution */}
        <div className={`card ${styles.chartCard} ${styles.chartCardSmall}`}>
          <div className={styles.chartHeader}>
            <h3>Threat Types</h3>
          </div>
          {loading || !distribution.length ? (
            <div className={styles.emptyState}>
              <p>No threat data yet.</p>
              <p className="text-sm">Add IOCs to see distribution.</p>
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={distribution}
                    dataKey="count"
                    nameKey="threat_type"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={2}
                  >
                    {distribution.map((_, i) => (
                      <Cell key={i} fill={THREAT_COLORS[i % THREAT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className={styles.legendList}>
                {distribution.slice(0, 6).map((item, i) => (
                  <div key={item.threat_type} className={styles.legendItem}>
                    <span className={styles.legendDot} style={{ background: THREAT_COLORS[i % THREAT_COLORS.length] }} />
                    <span className={styles.legendName}>{item.threat_type}</span>
                    <span className={styles.legendCount}>{item.count}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className={styles.quickActions}>
        <h3 className={styles.sectionTitle}>Quick Actions</h3>
        <div className={styles.actionsGrid}>
          {[
            { href: '/alerts', label: 'Create Alert', icon: '🚨', color: '#FF3B3B' },
            { href: '/logs', label: 'Ingest Logs', icon: '📋', color: '#00D4FF' },
            { href: '/threats', label: 'Add IOC', icon: '🕵️', color: '#FFA500' },
            { href: '/ai-analyst', label: 'Ask AI Analyst', icon: '🤖', color: '#A855F7' },
            { href: '/reports', label: 'Generate Report', icon: '📊', color: '#00C896' },
            { href: '/assets', label: 'Add Asset', icon: '🖥️', color: '#6B8DB2' },
          ].map(action => (
            <a key={action.href} href={action.href} className={styles.actionCard}>
              <span className={styles.actionIcon} style={{ background: `${action.color}1A`, border: `1px solid ${action.color}33` }}>
                {action.icon}
              </span>
              <span className={styles.actionLabel}>{action.label}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
