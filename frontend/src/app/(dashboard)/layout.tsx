'use client';

import { useState } from 'react';
import DashboardSidebar from '@/components/layout/DashboardSidebar';
import DashboardHeader from '@/components/layout/DashboardHeader';
import MobileBottomNav from '@/components/layout/MobileBottomNav';
import NowQueueDock from '@/components/layout/NowQueueDock';
import FloatingChatbot from '@/components/ai-chat/FloatingChatbot';
import dynamic from 'next/dynamic';

const CommandPalette = dynamic(() => import('@/components/ai-chat/CommandPalette'), { ssr: false });
import { useAuth } from '@/lib/providers/AuthProvider';
import { usePartnerTenantContext } from '@/lib/partner/tenantContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, hydrated } = useAuth();
  const { effectiveTenantId } = usePartnerTenantContext();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!hydrated) return;

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hydrated, isAuthenticated, router]);

  if (!hydrated) {
    return (
      <div className="flex items-center justify-center p-8" role="status" aria-label="Loading application">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-bg dashboard-surface">
      {/* Skip to content link (WCAG 2.4.1) */}
      <a href="#main-content" className="skip-to-content">
        Skip to main content
      </a>

      <DashboardSidebar
        mobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <DashboardHeader
          onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)}
        />
        <main
          id="main-content"
          className="dashboard-main flex-1 overflow-y-auto pb-36 lg:pb-32"
          role="main"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
      <MobileBottomNav onMore={() => setMobileMenuOpen(true)} />
      {effectiveTenantId && <NowQueueDock tenantId={effectiveTenantId} />}
      {/* AI Command Palette — Cmd+K to open */}
      {effectiveTenantId && <CommandPalette tenantId={effectiveTenantId} />}
      {/* AI Chatbot - appears on all dashboard pages */}
      {effectiveTenantId && <FloatingChatbot tenantId={effectiveTenantId} />}
    </div>
  );
}
