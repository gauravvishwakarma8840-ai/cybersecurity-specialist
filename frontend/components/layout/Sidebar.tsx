'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import styles from './Sidebar.module.css';

const NAV_ITEMS = [
  {
    group: 'Overview',
    items: [
      { href: '/dashboard',            label: 'Dashboard',          icon: <DashboardIcon /> },
    ],
  },
  {
    group: 'Security',
    items: [
      { href: '/alerts',               label: 'Alerts',             icon: <AlertIcon />,    badge: 'live' },
      { href: '/logs',                 label: 'Log Analysis',       icon: <LogIcon /> },
      { href: '/threats',              label: 'Threat Intel',       icon: <ThreatIcon /> },
      { href: '/vulnerabilities',      label: 'Vulnerabilities',    icon: <VulnIcon /> },
    ],
  },
  {
    group: 'Assets & AI',
    items: [
      { href: '/assets',               label: 'Assets',             icon: <AssetsIcon /> },
      { href: '/ai-analyst',           label: 'AI Analyst',         icon: <AIIcon />,       badge: 'new' },
      { href: '/reports',              label: 'Reports',            icon: <ReportIcon /> },
    ],
  },
  {
    group: 'Account',
    items: [
      { href: '/settings',             label: 'Settings',           icon: <SettingsIcon /> },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, organization, logout } = useAuth();

  return (
    <aside className={styles.sidebar}>
      {/* Logo */}
      <div className={styles.logoArea}>
        <div className={styles.logoIcon}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L3 7v5c0 5.25 3.75 10.1 9 11.4C17.25 22.1 21 17.25 21 12V7L12 2z" fill="url(#sidebar-shield)"/>
            <defs>
              <linearGradient id="sidebar-shield" x1="3" y1="2" x2="21" y2="23" gradientUnits="userSpaceOnUse">
                <stop stopColor="#00D4FF"/><stop offset="1" stopColor="#0066CC"/>
              </linearGradient>
            </defs>
            <path d="M9 12l2 2 4-4" stroke="#080C18" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div className={styles.logoText}>
          <span className={styles.logoName}>CyberSentinel</span>
          <span className={styles.orgName}>{organization?.name || 'Loading...'}</span>
        </div>
      </div>

      {/* Live Status */}
      <div className={styles.liveStatus}>
        <span className={styles.liveDot} />
        <span>System Online</span>
      </div>

      {/* Navigation */}
      <nav className={styles.nav}>
        {NAV_ITEMS.map(group => (
          <div key={group.group} className={styles.navGroup}>
            <div className={styles.navGroupLabel}>{group.group}</div>
            {group.items.map(item => {
              const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  <span className={styles.navLabel}>{item.label}</span>
                  {item.badge && (
                    <span className={`${styles.navBadge} ${styles[`navBadge--${item.badge}`]}`}>
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* User Profile */}
      <div className={styles.userArea}>
        <div className={styles.userAvatar}>
          {user?.full_name?.charAt(0).toUpperCase() || 'U'}
        </div>
        <div className={styles.userInfo}>
          <span className={styles.userName}>{user?.full_name || 'User'}</span>
          <span className={styles.userRole}>{user?.role || 'analyst'}</span>
        </div>
        <button
          className={styles.logoutBtn}
          onClick={logout}
          title="Logout"
          aria-label="Logout"
        >
          <LogoutIcon />
        </button>
      </div>
    </aside>
  );
}

// ─── Icons ───────────────────────────────────────────────────────────────────
function DashboardIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>;
}
function AlertIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>;
}
function LogIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>;
}
function ThreatIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>;
}
function VulnIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>;
}
function AssetsIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>;
}
function AIIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>;
}
function ReportIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>;
}
function SettingsIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 010 14.14M4.93 4.93a10 10 0 000 14.14"/></svg>;
}
function LogoutIcon() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>;
}
