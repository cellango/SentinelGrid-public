import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SentinelGrid | Developer source preview",
  description: "Review experimental security operations source, architecture, and implementation gaps.",
};

export default function HomePage() {
  return (
    <main className="min-h-screen bg-bg px-6 py-16 text-text-main">
      <section className="mx-auto max-w-3xl">
        <p className="text-sm font-semibold text-text-muted">Developer source preview</p>
        <h1 className="mt-4 text-4xl font-semibold">Review SentinelGrid with us.</h1>
        <p className="mt-6 text-lg leading-8 text-text-muted">
          SentinelGrid is experimental security operations source covering identity,
          detections, incidents, cloud posture, endpoint integrations, and AI workflows.
          This preview invites architecture review and developer comments. It is not
          a supported runnable platform or a hosted service offer.
        </p>
        <h2 className="mt-10 text-2xl font-semibold">Useful review topics</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-text-muted">
          <li>Tenant isolation, authorization, and approval boundaries</li>
          <li>Service ownership, model/migration consistency, and cloud adapters</li>
          <li>Reproducible checks, dependency decisions, and documentation clarity</li>
        </ul>
        <div className="mt-8 flex flex-wrap gap-5">
          <a className="underline" href="https://github.com/cellango/SentinelGrid-public">Review source and scope</a>
          <a className="underline" href="https://github.com/cellango/SentinelGrid-public/issues/new?template=review.yml">Share ordinary developer feedback</a>
          <a className="underline" href="/trust">Security review boundary</a>
        </div>
        <p className="mt-8 text-sm leading-6 text-text-muted">
          Read the repository README, release scope, licensing, and security policy
          before running commands. Use private reporting for vulnerabilities.
          Other product pages are experimental interface references.
        </p>
      </section>
    </main>
  );
}
