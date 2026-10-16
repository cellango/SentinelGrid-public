/**
 * Defense Coverage component
 * Shows MITRE/NIST coverage from detection rules/playbooks and highlights gaps vs a target baseline.
 */

'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listDetectionRules } from '@/lib/api/detection-rules';
import { playbooksApi } from '@/lib/api/playbooks';

type CoverageBuckets = {
  mitre_tactics: Set<string>;
  mitre_techniques: Set<string>;
  nist_controls: Set<string>;
};

const TARGET_TACTICS = ['TA0001', 'TA0002', 'TA0003', 'TA0004', 'TA0005', 'TA0006', 'TA0007', 'TA0008', 'TA0009', 'TA0010', 'TA0040'];
const TARGET_TECHNIQUES = ['T1078', 'T1110', 'T1021', 'T1059', 'T1055', 'T1486', 'T1566', 'T1047', 'T1041', 'T1071'];
const TARGET_NIST = ['AC-2', 'AC-6', 'AU-6', 'CA-7', 'CM-7', 'IA-5', 'IR-4', 'IR-5', 'IR-6', 'RA-3', 'SI-3', 'SI-4'];

const toSet = (arr?: string[]) => new Set((arr || []).filter(Boolean));

export function DefenseCoverage() {
  const { data: rules } = useQuery({
    queryKey: ['detection-rules'],
    queryFn: () => listDetectionRules(),
  });

  const { data: playbooks } = useQuery({
    queryKey: ['playbooks'],
    queryFn: () => playbooksApi.list(),
  });

  const coverage = useMemo<CoverageBuckets>(() => {
    const buckets: CoverageBuckets = {
      mitre_tactics: new Set<string>(),
      mitre_techniques: new Set<string>(),
      nist_controls: new Set<string>(),
    };
    const allRules = Array.isArray(rules) ? rules : [];
    const allPlaybooks = Array.isArray(playbooks) ? playbooks : [];

    allRules.forEach((rule: any) => {
      const mv = rule?.versions?.[0]?.metadata || {};
      (mv.mitre_tactics || []).forEach((t: string) => buckets.mitre_tactics.add(t));
      (mv.mitre_techniques || []).forEach((t: string) => buckets.mitre_techniques.add(t));
      (mv.nist_controls || []).forEach((c: string) => buckets.nist_controls.add(c));
    });
    allPlaybooks.forEach((pb: any) => {
      (pb.mitre_tactics || []).forEach((t: string) => buckets.mitre_tactics.add(t));
      (pb.mitre_techniques || []).forEach((t: string) => buckets.mitre_techniques.add(t));
      (pb.nist_controls || []).forEach((c: string) => buckets.nist_controls.add(c));
    });
    return buckets;
  }, [rules, playbooks]);

  const gaps = useMemo(() => {
    const gapTactics = TARGET_TACTICS.filter((t) => !coverage.mitre_tactics.has(t));
    const gapTechniques = TARGET_TECHNIQUES.filter((t) => !coverage.mitre_techniques.has(t));
    const gapNist = TARGET_NIST.filter((c) => !coverage.nist_controls.has(c));
    return { gapTactics, gapTechniques, gapNist };
  }, [coverage]);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <CoverageCard
          title="MITRE Tactics"
          covered={coverage.mitre_tactics.size}
          target={TARGET_TACTICS.length}
          items={Array.from(coverage.mitre_tactics)}
          gaps={gaps.gapTactics}
          linkBase="https://attack.mitre.org/tactics/"
        />
        <CoverageCard
          title="MITRE Techniques"
          covered={coverage.mitre_techniques.size}
          target={TARGET_TECHNIQUES.length}
          items={Array.from(coverage.mitre_techniques)}
          gaps={gaps.gapTechniques}
          linkBase="https://attack.mitre.org/techniques/"
        />
        <CoverageCard
          title="NIST Controls"
          covered={coverage.nist_controls.size}
          target={TARGET_NIST.length}
          items={Array.from(coverage.nist_controls)}
          gaps={gaps.gapNist}
          linkBase="/dashboard/compliance?control="
        />
      </div>
    </div>
  );
}

function CoverageCard({
  title,
  covered,
  target,
  items,
  gaps,
  linkBase,
}: {
  title: string;
  covered: number;
  target: number;
  items: string[];
  gaps: string[];
  linkBase: string;
}) {
  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-text-main">{title}</h3>
          <p className="text-sm text-text-muted">{covered} / {target} covered</p>
        </div>
        <span className="px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs">
          Gaps: {gaps.length}
        </span>
      </div>
      <div className="text-sm text-text-muted">
        <div className="mb-1 font-medium">Covered</div>
        <div className="flex flex-wrap gap-2">
          {items.length ? items.map((it) => (
            <a
              key={it}
              href={`${linkBase}${it}`}
              target={linkBase.startsWith('http') ? '_blank' : undefined}
              rel="noreferrer"
              className="px-2 py-1 rounded bg-green-100 text-green-700 text-xs hover:bg-green-200"
            >
              {it}
            </a>
          )) : <span className="text-text-muted text-xs">None yet</span>}
        </div>
      </div>
      <div className="text-sm text-text-muted">
        <div className="mb-1 font-medium">Gaps</div>
        <div className="flex flex-wrap gap-2">
          {gaps.length ? gaps.map((it) => (
            <a
              key={it}
              href={`${linkBase}${it}`}
              target={linkBase.startsWith('http') ? '_blank' : undefined}
              rel="noreferrer"
              className="px-2 py-1 rounded bg-amber-100 text-amber-700 text-xs hover:bg-amber-200"
            >
              {it}
            </a>
          )) : <span className="text-text-muted text-xs">No gaps vs target set</span>}
        </div>
      </div>
    </div>
  );
}
