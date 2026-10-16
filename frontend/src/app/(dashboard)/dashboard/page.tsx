'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  DASHBOARD_PERSONAS,
  getDashboardLandingHref,
  getMatchingPersonas,
  setStoredDashboardPersona,
} from '@/lib/dashboard/personas';

export default function DashboardLandingPage() {
  const router = useRouter();
  const { hydrated, user } = useAuth();
  const [isMobile, setIsMobile] = useState(false);
  const [redirectComplete, setRedirectComplete] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mediaQuery = window.matchMedia('(max-width: 1023px)');
    const sync = () => setIsMobile(mediaQuery.matches);
    sync();
    mediaQuery.addEventListener('change', sync);
    return () => mediaQuery.removeEventListener('change', sync);
  }, []);

  const matchingPersonas = useMemo(() => getMatchingPersonas(user?.roles), [user?.roles]);
  const landingHref = useMemo(
    () =>
      hydrated
        ? getDashboardLandingHref({
            roles: user?.roles,
            isMobile,
          })
        : null,
    [hydrated, user?.roles, isMobile]
  );
  const shouldShowChooser = hydrated && !isMobile && !landingHref && matchingPersonas.length >= 2;

  useEffect(() => {
    if (!hydrated) return;
    if (landingHref) {
      setRedirectComplete(true);
      router.replace(landingHref);
      return;
    }
    if (shouldShowChooser) {
      setRedirectComplete(true);
      return;
    }
    setRedirectComplete(true);
    router.replace('/dashboard/now');
  }, [hydrated, landingHref, router, shouldShowChooser]);

  if (!hydrated || !redirectComplete) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm text-text-muted">Preparing your workspace…</p>
        </div>
      </div>
    );
  }

  if (!shouldShowChooser) {
    return null;
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-10rem)] max-w-5xl items-center px-4 py-10 sm:px-6">
      <div className="w-full rounded-3xl border border-primary/20 bg-surface-card p-6 shadow-2xl shadow-primary/10 sm:p-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
          Choose your default landing view
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-text-main">
          Open the workflow that matches how you use SentinelGrid
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
          Your account roles match more than one operator persona. Pick the view that should open first on desktop.
          Mobile keeps the Now queue as the default so urgent triage stays one tap away.
        </p>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {matchingPersonas.map((persona) => (
            <button
              key={persona.id}
              type="button"
              onClick={() => {
                setStoredDashboardPersona(persona.id);
                router.replace(isMobile ? persona.mobileLandingHref || '/dashboard/now' : persona.landingHref);
              }}
              className="rounded-2xl border border-border-faint bg-bg-alt p-5 text-left transition-colors hover:border-primary/40 hover:bg-surface-hover"
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                {persona.workflow}
              </p>
              <h2 className="mt-2 text-xl font-semibold text-text-main">{persona.label}</h2>
              <p className="mt-2 text-sm leading-6 text-text-muted">{persona.description}</p>
              <p className="mt-4 text-sm font-medium text-primary">
                Open {persona.landingHref.replace('/dashboard/', '')}
              </p>
            </button>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            href="/dashboard/now"
            className="inline-flex min-h-[44px] items-center rounded-xl border border-border-strong px-4 py-2 text-sm text-text-main transition-colors hover:border-primary"
          >
            Open the Now queue instead
          </Link>
          <button
            type="button"
            onClick={() => {
              setStoredDashboardPersona(DASHBOARD_PERSONAS.soc_analyst.id);
              router.replace('/dashboard/incidents');
            }}
            className="inline-flex min-h-[44px] items-center rounded-xl bg-primary px-4 py-2 text-sm font-medium text-slate-950 transition-all hover:brightness-110"
          >
            Use the analyst default
          </button>
        </div>
      </div>
    </div>
  );
}
