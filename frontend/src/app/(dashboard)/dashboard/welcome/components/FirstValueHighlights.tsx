'use client';

import Link from 'next/link';
import type {
  CloudPostureSnapshot,
  DashboardHealth,
  FirstValueFinding,
  OpenIncident,
  PeopleAccessSnapshot,
  PostureScore,
  Recommendation,
} from '@/lib/api/dashboard';
import type { OnboardingStatus } from '@/lib/api/onboarding';
import { buildOnboardingActivationSummary } from '@/lib/onboarding/activation';
import { recordOnboardingCtaClick } from '@/lib/onboarding/metrics';
import { getRecommendationHref } from '@/lib/dashboard/recommendations';

type HighlightCard = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  ctaLabel: string;
};

interface FirstValueHighlightsProps {
  prioritizedFindings?: FirstValueFinding[];
  recommendations: Recommendation[];
  incidents: OpenIncident[];
  cloudPosture?: CloudPostureSnapshot;
  peopleAccess?: PeopleAccessSnapshot;
  postureScore?: PostureScore;
  health?: DashboardHealth;
  onboardingStatus?: OnboardingStatus | null;
}

export default function FirstValueHighlights({
  prioritizedFindings = [],
  recommendations,
  incidents,
  cloudPosture,
  peopleAccess,
  postureScore,
  health,
  onboardingStatus = null,
}: FirstValueHighlightsProps) {
  const onboardingSummary = buildOnboardingActivationSummary(onboardingStatus);
  const ticketingItem = onboardingSummary.items.find((item) => item.id === 'ticketing');
  const ticketingNeedsAttention =
    onboardingStatus?.services_selected?.socManaged === false &&
    (onboardingStatus?.ticketing_health?.status || 'unknown') !== 'healthy';

  const findings: HighlightCard[] = prioritizedFindings.map((finding) => ({
    id: finding.id,
    eyebrow: finding.eyebrow,
    title: finding.title,
    description: finding.description,
    href: finding.href,
    ctaLabel: finding.cta_label,
  }));
  const quickWins: HighlightCard[] = [];

  if (findings.length === 0 && incidents.length > 0) {
    const incident = incidents[0];
    findings.push({
      id: `incident-${incident.id}`,
      eyebrow: 'Active incident',
      title: incident.title,
      description:
        incident.story_summary?.detail ||
        `${incident.affected_count} ${
          incident.affected_count === 1 ? 'item is' : 'items are'
        } affected. Start here if you need immediate investigation context.`,
      href: `/dashboard/incidents/${incident.id}`,
      ctaLabel: 'Investigate incident',
    });
  }

  if (findings.length < 3 && cloudPosture && cloudPosture.critical_misconfigs > 0) {
    findings.push({
      id: 'cloud-risk',
      eyebrow: 'Cloud finding',
      title: cloudPosture.biggest_risk?.title || `${cloudPosture.critical_misconfigs} critical cloud issues`,
      description:
        cloudPosture.biggest_risk?.description ||
        `SentinelGrid has already surfaced ${cloudPosture.critical_misconfigs} critical cloud issues worth triaging first.`,
      href: '/dashboard/compliance',
      ctaLabel: 'Review posture',
    });
  }

  if (findings.length < 3 && peopleAccess && peopleAccess.mfa_missing_count > 0) {
    findings.push({
      id: 'identity-gap',
      eyebrow: 'Identity finding',
      title: `${peopleAccess.mfa_missing_count} ${
        peopleAccess.mfa_missing_count === 1 ? 'user is' : 'users are'
      } missing MFA`,
      description:
        'This is usually one of the fastest, highest-signal fixes for new tenants after identity is connected.',
      href: '/dashboard/iam/people',
      ctaLabel: 'Fix MFA gaps',
    });
  }

  if (findings.length < 3 && postureScore?.top_risks?.length) {
    const risk = postureScore.top_risks[0];
    findings.push({
      id: `posture-risk-${risk.id || risk.title}`,
      eyebrow: 'Top risk',
      title: risk.title,
      description:
        'SentinelGrid is already correlating this into your posture view so the team can decide whether to remediate or accept the risk.',
      href: '/dashboard/posture',
      ctaLabel: 'Inspect top risk',
    });
  }

  recommendations.slice(0, 3).forEach((rec) => {
    quickWins.push({
      id: rec.id,
      eyebrow: `${rec.priority === 'critical' ? 'Immediate action' : 'Quick win'} · ${rec.estimated_time_minutes} min`,
      title: rec.title,
      description: rec.description,
      href: getRecommendationHref(rec),
      ctaLabel: rec.actions[0]?.label || 'Open recommendation',
    });
  });

  if (quickWins.length < 3 && health?.integrations?.endpoint !== 'connected') {
    quickWins.push({
      id: 'endpoint-coverage',
      eyebrow: 'Coverage',
      title: 'Deploy endpoint coverage next',
      description:
        'Endpoint coverage closes the loop between posture findings and response workflows, especially once cloud and identity are connected.',
      href: '/dashboard/endpoint-protection',
      ctaLabel: 'Open endpoint coverage',
    });
  }

  if (quickWins.length < 3 && ticketingNeedsAttention && ticketingItem) {
    quickWins.push({
      id: 'ticketing-handoff',
      eyebrow: 'Collaboration',
      title: 'Finish the incident handoff',
      description:
        'Define where incidents land, who owns them, and whether Slack should receive the first-week escalation notifications.',
      href: ticketingItem.href,
      ctaLabel: 'Configure handoff',
    });
  }

  if (quickWins.length < 3 && onboardingSummary.pendingItems.length > 0) {
    const nextItem = onboardingSummary.pendingItems[0];
    quickWins.push({
      id: `onboarding-${nextItem.id}`,
      eyebrow: 'Onboarding',
      title: `Finish ${nextItem.label.toLowerCase()}`,
      description: nextItem.description,
      href: nextItem.href,
      ctaLabel: nextItem.ctaLabel,
    });
  }

  const visibleFindings = findings.slice(0, 3);
  const visibleQuickWins = quickWins.slice(0, 3);

  if (visibleFindings.length === 0 && visibleQuickWins.length === 0) {
    return null;
  }

  return (
    <div className="mb-8 grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
      <section className="rounded-2xl border border-primary/20 bg-[rgba(15,23,42,0.9)] p-6 backdrop-blur-md">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
            First findings
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-text-main">
            What SentinelGrid is already surfacing
          </h2>
          <p className="mt-2 text-sm text-text-muted">
            Focus the team on the first issues that are worth action instead of scrolling across separate modules.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {visibleFindings.map((finding) => (
            <div
              key={finding.id}
              className="rounded-xl border border-primary/10 bg-slate-950/50 p-4"
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                {finding.eyebrow}
              </p>
              <h3 className="mt-3 text-lg font-semibold text-text-main">{finding.title}</h3>
              <p className="mt-2 text-sm leading-6 text-text-muted">{finding.description}</p>
              <Link
                href={finding.href}
                onClick={() =>
                  recordOnboardingCtaClick({
                    source: 'welcome_first_value_finding',
                    target: finding.href,
                    stepId: finding.id,
                  })
                }
                className="mt-4 inline-flex items-center text-sm font-medium text-primary hover:text-primary/80"
              >
                {finding.ctaLabel} →
              </Link>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-primary/20 bg-[rgba(15,23,42,0.9)] p-6 backdrop-blur-md">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
            Quick wins
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-text-main">
            Best next actions this week
          </h2>
          <p className="mt-2 text-sm text-text-muted">
            Keep the first week focused on the actions most likely to improve coverage and reduce obvious risk.
          </p>
        </div>
        <div className="space-y-3">
          {visibleQuickWins.map((quickWin) => (
            <div
              key={quickWin.id}
              className="rounded-xl border border-primary/10 bg-slate-950/50 p-4"
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                {quickWin.eyebrow}
              </p>
              <h3 className="mt-2 text-base font-semibold text-text-main">{quickWin.title}</h3>
              <p className="mt-2 text-sm leading-6 text-text-muted">{quickWin.description}</p>
              <Link
                href={quickWin.href}
                onClick={() =>
                  recordOnboardingCtaClick({
                    source: 'welcome_first_value_quick_win',
                    target: quickWin.href,
                    stepId: quickWin.id,
                  })
                }
                className="mt-3 inline-flex items-center text-sm font-medium text-primary hover:text-primary/80"
              >
                {quickWin.ctaLabel} →
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
