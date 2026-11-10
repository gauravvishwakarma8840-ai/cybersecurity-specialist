'use client';

import { useEffect, useState, useRef } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { dashboardApi, notificationsApi, type NotificationItem } from '@/lib/api';
import styles from './Header.module.css';

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/dashboard':                    { title: 'Security Dashboard',  subtitle: 'Real-time threat overview' },
  '/alerts':                       { title: 'Alert Management',    subtitle: 'Monitor and respond to security alerts' },
  '/dashboard/alerts':             { title: 'Alert Management',    subtitle: 'Monitor and respond to security alerts' },
  '/logs':                         { title: 'Log Analysis',        subtitle: 'Ingest and analyze security logs' },
  '/dashboard/logs':               { title: 'Log Analysis',        subtitle: 'Ingest and analyze security logs' },
  '/threats':                      { title: 'Threat Intelligence', subtitle: 'IOC tracking and enrichment' },
  '/dashboard/threats':            { title: 'Threat Intelligence', subtitle: 'IOC tracking and enrichment' },
  '/vulnerabilities':              { title: 'Vulnerabilities',     subtitle: 'CVE tracking and risk management' },
  '/dashboard/vulnerabilities':    { title: 'Vulnerabilities',     subtitle: 'CVE tracking and risk management' },
  '/assets':                       { title: 'Asset Inventory',     subtitle: 'IT asset management and exposure tracking' },
  '/dashboard/assets':             { title: 'Asset Inventory',     subtitle: 'IT asset management and exposure tracking' },
  '/ai-analyst':                   { title: 'AI Security Analyst', subtitle: 'Gemini-powered threat analysis chatbot' },
  '/dashboard/ai-analyst':         { title: 'AI Security Analyst', subtitle: 'Gemini-powered threat analysis chatbot' },
  '/reports':                      { title: 'Security Reports',    subtitle: 'On-demand and scheduled reports' },
  '/dashboard/reports':            { title: 'Security Reports',    subtitle: 'On-demand and scheduled reports' },
  '/settings':                     { title: 'Settings',            subtitle: 'Organization and account management' },
  '/dashboard/settings':           { title: 'Settings',            subtitle: 'Organization and account management' },
};

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuth();
  const page = PAGE_TITLES[pathname] ?? { title: 'CyberSentinel AI', subtitle: '' };

  const [timeStr, setTimeStr] = useState<string>('');
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [showDropdown, setShowDropdown] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [threatLevel, setThreatLevel] = useState<{ label: string; color: string; bg: string }>({
    label: 'Guarded',
    color: 'var(--color-medium)',
    bg: 'rgba(255, 165, 0, 0.08)',
  });

  // Live UTC Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toUTCString().slice(17, 25));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch initial notifications and threat level
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const notifRes = await notificationsApi.list({ unread_only: false });
        setNotifications(notifRes.items.slice(0, 10));
        setUnreadCount(notifRes.unread_count);
      } catch (err) {
        console.error('Failed to load notifications:', err);
      }

      try {
        const stats = await dashboardApi.getStats();
        if (stats.critical_alerts >= 3) {
          setThreatLevel({
            label: 'DEFCON 1 / Critical',
            color: 'var(--color-critical)',
            bg: 'rgba(255, 68, 68, 0.15)',
          });
        } else if (stats.critical_alerts > 0) {
          setThreatLevel({
            label: 'Elevated',
            color: 'var(--color-critical)',
            bg: 'rgba(255, 68, 68, 0.10)',
          });
        } else if (stats.open_alerts > 0) {
          setThreatLevel({
            label: 'Guarded',
            color: 'var(--color-medium)',
            bg: 'rgba(255, 165, 0, 0.08)',
          });
        } else {
          setThreatLevel({
            label: 'Normal',
            color: 'var(--color-success)',
            bg: 'rgba(0, 200, 83, 0.08)',
          });
        }
      } catch (err) {
        console.error('Failed to load stats for threat level:', err);
      }
    };

    fetchStatus();

    // WebSocket real-time event listener
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (!token) return;

    let ws: WebSocket | null = null;
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/v1/ws?token=${token}`;

      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.notification) {
            setNotifications((prev) => [
              {
                id: msg.notification.id || String(Date.now()),
                org_id: '',
                user_id: null,
                title: msg.notification.title,
                message: msg.notification.message || '',
                severity: msg.notification.severity || 'info',
                is_read: false,
                link: msg.notification.link || null,
                created_at: new Date().toISOString(),
              },
              ...prev.slice(0, 9),
            ]);
            setUnreadCount((count) => count + 1);
          }
        } catch {
          // ignore
        }
      };
    } catch (wsErr) {
      console.warn('WebSocket setup skipped:', wsErr);
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkRead = async (id: string, link: string | null) => {
    try {
      await notificationsApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
      if (link) {
        setShowDropdown(false);
        router.push(link);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <h2 className={styles.title}>{page.title}</h2>
        {page.subtitle && <p className={styles.subtitle}>{page.subtitle}</p>}
      </div>

      <div className={styles.right}>
        {/* Threat Level Indicator */}
        <div
          className={styles.threatLevel}
          style={{ background: threatLevel.bg, borderColor: threatLevel.color }}
        >
          <span
            className={styles.threatLevelDot}
            style={{ background: threatLevel.color }}
          />
          <span className={styles.threatLevelText} style={{ color: threatLevel.color }}>
            Threat Level: <strong>{threatLevel.label}</strong>
          </span>
        </div>

        {/* UTC Clock */}
        <div className={styles.clock}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <span className="font-mono" style={{ fontSize: '0.8rem' }}>
            {timeStr || '00:00:00'} UTC
          </span>
        </div>

        {/* Notification Bell with Dropdown */}
        <div style={{ position: 'relative' }} ref={dropdownRef}>
          <button
            className={styles.iconBtn}
            aria-label="Notifications"
            title="Notifications"
            onClick={() => setShowDropdown((open) => !open)}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 01-3.46 0" />
            </svg>
            {unreadCount > 0 && <span className={styles.notifBadge}>{unreadCount > 9 ? '9+' : unreadCount}</span>}
          </button>

          {showDropdown && (
            <div
              style={{
                position: 'absolute',
                top: 48,
                right: 0,
                width: 360,
                background: 'var(--color-bg-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: '0 12px 32px rgba(0, 0, 0, 0.4)',
                zIndex: 100,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  borderBottom: '1px solid var(--color-border)',
                }}
              >
                <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                  Notifications {unreadCount > 0 && <span style={{ color: 'var(--color-critical)' }}>({unreadCount})</span>}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-cyan)',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div style={{ maxHeight: 360, overflowY: 'auto' }}>
                {notifications.length === 0 ? (
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
                    No notifications yet.
                  </div>
                ) : (
                  notifications.map((notif) => (
                    <div
                      key={notif.id}
                      onClick={() => handleMarkRead(notif.id, notif.link)}
                      style={{
                        padding: '12px 16px',
                        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                        background: notif.is_read ? 'transparent' : 'rgba(0, 212, 255, 0.04)',
                        cursor: 'pointer',
                        transition: 'background 0.2s',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 4,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span
                          style={{
                            fontWeight: notif.is_read ? 500 : 700,
                            fontSize: '0.82rem',
                            color: notif.severity === 'critical' ? 'var(--color-critical)' : 'var(--color-text-primary)',
                          }}
                        >
                          {notif.title}
                        </span>
                        {!notif.is_read && (
                          <span
                            style={{
                              width: 6,
                              height: 6,
                              borderRadius: '50%',
                              background: 'var(--color-cyan)',
                            }}
                          />
                        )}
                      </div>
                      {notif.message && (
                        <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-text-muted)', lineHeight: 1.3 }}>
                          {notif.message}
                        </p>
                      )}
                      <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>
                        {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Avatar */}
        <div className={styles.userChip}>
          <div className={styles.userAvatar}>
            {user?.full_name?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className={styles.userDetails}>
            <span className={styles.userName}>{user?.full_name?.split(' ')[0]}</span>
            <span className={styles.userRole}>{user?.role}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
