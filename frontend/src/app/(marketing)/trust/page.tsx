import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SentinelGrid | Source preview security boundary",
  description: "Source-review scope, limitations, and private vulnerability reporting.",
};

export default function TrustPage() {
  return (
    <main className="min-h-screen bg-bg px-6 py-16 text-text-main">
      <section className="mx-auto max-w-3xl">
        <h1 className="text-4xl font-semibold">Source preview security boundary</h1>
        <p className="mt-6 text-lg leading-8 text-text-muted">
          This preview provides source and focused local checks. It does not certify
          production readiness, compliance, live tenant isolation, retention guarantees,
          or a supported customer service. Historical trust and launch documents do
          not establish the current release boundary.
        </p>
        <p className="mt-6 leading-7 text-text-muted">
          Review the repository security policy for known limitations and private
          reporting. Private-reporting availability and monitored contact verification
          remain publication gates. If the private form is unavailable, request a
          contact without disclosing vulnerability details in a public issue.
        </p>
        <div className="mt-8 flex flex-wrap gap-5">
          <a className="underline" href="https://github.com/cellango/SentinelGrid-public/blob/main/SECURITY.md">Security policy and reporting</a>
          <a className="underline" href="https://github.com/cellango/SentinelGrid-public/blob/main/RELEASE_SCOPE.md">Verified scope and limitations</a>
          <a className="underline" href="/">Developer preview</a>
        </div>
      </section>
    </main>
  );
}
