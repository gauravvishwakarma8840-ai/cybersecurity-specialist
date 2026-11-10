'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import styles from '../login/auth.module.css';

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    full_name: '', email: '', password: '', confirmPassword: '',
    org_name: '', org_slug: '',
  });

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value;
    // Auto-generate slug from org name
    if (field === 'org_name') {
      setForm(prev => ({
        ...prev,
        org_name: value,
        org_slug: value.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').slice(0, 50),
      }));
      return;
    }
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }

    setIsLoading(true);
    try {
      await register({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        org: { name: form.org_name, slug: form.org_slug },
      });
      router.push('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.authPage}>
      <div className={styles.bgGrid} aria-hidden />
      <div className={styles.bgOrb1} aria-hidden />
      <div className={styles.bgOrb2} aria-hidden />

      <div className={styles.authCard} style={{ maxWidth: 520 }}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L3 7v5c0 5.25 3.75 10.1 9 11.4C17.25 22.1 21 17.25 21 12V7L12 2z" fill="url(#shield-grad2)"/>
              <defs>
                <linearGradient id="shield-grad2" x1="3" y1="2" x2="21" y2="23" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#00D4FF"/><stop offset="1" stopColor="#0066CC"/>
                </linearGradient>
              </defs>
              <path d="M9 12l2 2 4-4" stroke="#080C18" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <h1 className={styles.logoName}>CyberSentinel AI</h1>
            <p className={styles.logoTagline}>Create your organization</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.sectionLabel}>Personal Info</div>

          <div className={styles.formRow}>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input id="full_name" className="form-input" type="text" placeholder="Alex Johnson" value={form.full_name} onChange={set('full_name')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input id="email" className="form-input" type="email" placeholder="you@company.com" value={form.email} onChange={set('email')} required />
            </div>
          </div>

          <div className={styles.formRow}>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input id="password" className="form-input" type="password" placeholder="Min. 12 characters" value={form.password} onChange={set('password')} required minLength={12} />
            </div>
            <div className="form-group">
              <label className="form-label">Confirm Password</label>
              <input id="confirm_password" className="form-input" type="password" placeholder="Repeat password" value={form.confirmPassword} onChange={set('confirmPassword')} required />
            </div>
          </div>

          <div className={styles.divider} />
          <div className={styles.sectionLabel}>Organization</div>

          <div className={styles.formRow}>
            <div className="form-group">
              <label className="form-label">Organization Name</label>
              <input id="org_name" className="form-input" type="text" placeholder="Acme Security Corp" value={form.org_name} onChange={set('org_name')} required />
            </div>
            <div className="form-group">
              <label className="form-label">URL Slug</label>
              <input id="org_slug" className="form-input" type="text" placeholder="acme-security" value={form.org_slug} onChange={set('org_slug')} required pattern="^[a-z0-9\-]+$" />
            </div>
          </div>

          {error && (
            <div className={styles.errorAlert} role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
              </svg>
              {error}
            </div>
          )}

          <button type="submit" id="register-submit" className="btn btn--primary w-full" disabled={isLoading}>
            {isLoading ? <><span className={styles.spinner} /> Creating account...</> : 'Create Organization & Account'}
          </button>
        </form>

        <p className={styles.authSwitch}>
          Already have an account? <Link href="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
