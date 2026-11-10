"""
Database Seeder Script — Seeds demo organization, admin user, sample alerts, threats, and assets.
Usage: python seed_db.py
"""
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.threat import ThreatIndicator, IndicatorType
from app.models.asset import Asset, AssetType
from app.models.vulnerability import Vulnerability, VulnSeverity, VulnStatus
from app.models.log_entry import LogEntry, LogSeverity

async def seed_data():
    # Force SQLite fallback for local development if Postgres is not running
    db_url = "sqlite+aiosqlite:///./cybersentinel.db"
    connect_args = {"check_same_thread": False}

    engine = create_async_engine(db_url, echo=False, connect_args=connect_args)
    
    # Create tables automatically
    from app.core.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("[+] Seeding CyberSentinel AI Demo Data...")

        # 1. Demo Organization
        org = Organization(
            id=uuid4(),
            name="CyberSentinel Defense Corp",
            slug="cybersentinel-demo",
            plan="enterprise",
            is_active=True,
        )
        session.add(org)
        await session.flush()

        # 2. Demo Admin User
        admin_user = User(
            id=uuid4(),
            org_id=org.id,
            email="admin@cybersentinel.com",
            password_hash=hash_password("Admin@12345678"),
            full_name="Alex Mercer (SOC Lead)",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)

        # 3. Sample Alerts
        alerts_data = [
            ("SSH Brute Force Attack Detected", AlertSeverity.CRITICAL, "auth_brute_force", "192.168.1.105", "10.0.0.12", "T1110", "Brute Force", 92.5),
            ("SQL Injection Attempt on API Endpoint", AlertSeverity.HIGH, "sqli_attempt", "45.33.32.156", "10.0.0.5", "T1190", "Exploit Public-Facing Application", 78.0),
            ("Unauthorized Powershell Encoded Command", AlertSeverity.HIGH, "suspicious_powershell", "10.0.0.45", "10.0.0.45", "T1059.001", "PowerShell", 68.4),
            ("Port Scan from External IP", AlertSeverity.MEDIUM, "port_scan", "185.220.101.5", "10.0.0.1", "T1046", "Network Service Discovery", 45.0),
            ("Outbound Connection to Known Malicious C2", AlertSeverity.CRITICAL, "c2_traffic", "10.0.0.88", "198.51.100.42", "T1071", "Application Layer Protocol", 95.0),
        ]
        for title, sev, atype, src, dst, tech, tac, score in alerts_data:
            session.add(Alert(
                org_id=org.id,
                title=title,
                description=f"Automated security detection: {title}. Immediate analyst review recommended.",
                severity=sev,
                status=AlertStatus.OPEN,
                alert_type=atype,
                source_ip=src,
                dest_ip=dst,
                mitre_technique=tech,
                mitre_tactic=tac,
                risk_score=score,
                ai_summary=f"Automated AI Summary: Detected high-confidence anomaly matching pattern '{atype}'. Recommended action: Isolate source host {src} and inspect process logs.",
            ))

        # 4. Sample Threat IOCs
        threats_data = [
            (IndicatorType.IP, "198.51.100.42", "c2", 0.95, 88, "US"),
            (IndicatorType.DOMAIN, "malicious-update-server.com", "malware", 0.90, 75, "RU"),
            (IndicatorType.FILE_HASH_SHA256, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "ransomware", 1.0, 99, None),
        ]
        for itype, val, ttype, conf, abuse, cc in threats_data:
            session.add(ThreatIndicator(
                org_id=org.id,
                indicator_type=itype,
                value=val,
                threat_type=ttype,
                confidence_score=conf,
                abuse_confidence=abuse,
                country_code=cc,
                source="CyberSentinel Threat Feed",
                is_active=True,
            ))

        # 5. Sample Assets
        assets_data = [
            ("prod-web-01", "10.0.0.5", "Ubuntu 22.04 LTS", AssetType.SERVER, "DevOps Team", True, 45.0),
            ("prod-db-master", "10.0.0.12", "PostgreSQL Server on Debian 12", AssetType.SERVER, "DBA Team", False, 15.0),
            ("sec-analyst-laptop-01", "10.0.0.88", "macOS Sonoma 14.5", AssetType.WORKSTATION, "Alex Mercer", False, 85.0),
        ]
        for host, ip, os_name, atype, owner, is_pub, rscore in assets_data:
            session.add(Asset(
                org_id=org.id,
                hostname=host,
                ip_address=ip,
                os_type=os_name,
                asset_type=atype,
                owner=owner,
                is_internet_facing=is_pub,
                risk_score=rscore,
                is_active=True,
            ))

        # 6. Sample Vulnerabilities
        vulns_data = [
            ("CVE-2024-3094", "XZ Utils Backdoor RCE", 10.0, VulnSeverity.CRITICAL, True, True),
            ("CVE-2023-4863", "Heap buffer overflow in libwebp", 8.8, VulnSeverity.HIGH, True, True),
            ("CVE-2024-21626", "runc Container Breakout", 8.6, VulnSeverity.HIGH, True, False),
        ]
        for cve, title, cvss, sev, patch, exp in vulns_data:
            session.add(Vulnerability(
                org_id=org.id,
                cve_id=cve,
                title=title,
                description=f"Critical vulnerability {cve}: {title}. Upgrade immediately.",
                cvss_score=cvss,
                severity=sev,
                status=VulnStatus.OPEN,
                patch_available=patch,
                exploit_available=exp,
            ))

        await session.commit()
        print("[+] Demo Data Successfully Seeded!")
        print("\n[*] Demo Login Credentials:")
        print("   Email:    admin@cybersentinel.com")
        print("   Password: Admin@12345678")
        print("   Org:      CyberSentinel Defense Corp")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_data())
