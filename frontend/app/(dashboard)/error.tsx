'use client';

import { useEffect } from 'react';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Dashboard Error:', error);
  }, [error]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '50vh',
        gap: 16,
        textAlign: 'center',
        padding: 32,
      }}
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          background: 'rgba(255, 68, 68, 0.1)',
          border: '1px solid var(--color-critical)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.5rem',
        }}
      >
        ⚠️
      </div>

      <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
        An unexpected error occurred in this view
      </h2>

      <p style={{ color: 'var(--color-text-muted)', maxWidth: 440, fontSize: '0.875rem', margin: 0 }}>
        {error.message || 'Unable to load security telemetry. Please verify your connection or retry.'}
      </p>

      <button className="btn btn--primary btn--sm" onClick={() => reset()} style={{ marginTop: 8 }}>
        ↻ Try Again
      </button>
    </div>
  );
}

