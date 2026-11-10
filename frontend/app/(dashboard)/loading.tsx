export default function DashboardLoading() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, width: '100%' }}>
      {/* Skeleton KPI Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div className="skeleton" style={{ width: '50%', height: 14 }} />
            <div className="skeleton" style={{ width: '80%', height: 28 }} />
          </div>
        ))}
      </div>

      {/* Skeleton Content Card */}
      <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="skeleton" style={{ width: '30%', height: 20 }} />
        <div className="skeleton" style={{ width: '100%', height: 260 }} />
      </div>
    </div>
  );
}

