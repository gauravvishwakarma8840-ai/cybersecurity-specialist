import type { Metadata } from 'next';
import { AuthProvider } from '@/lib/auth';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: { default: 'CyberSentinel AI', template: '%s | CyberSentinel AI' },
  description: 'AI-First Cybersecurity SaaS Platform — Real-time threat detection, intelligent alert management, and AI-powered security analysis.',
  keywords: ['cybersecurity', 'SIEM', 'threat intelligence', 'security operations', 'AI security'],
  robots: 'noindex, nofollow',  // Security tool — not for public indexing
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
