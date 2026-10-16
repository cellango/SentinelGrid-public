"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  createDemoRequest,
  type DemoAIShieldFit,
  type DemoIdentityProfile,
  type DemoRetentionProfile,
  type DemoRolloutScope,
} from "@/lib/api/leads";
import { trackMarketingEvent } from "@/lib/marketing/analytics";
import {
  isMarketingPlanKey,
  marketingPlans,
  type MarketingPlanKey,
} from "@/lib/marketing/packages";

type DemoQualificationReason =
  | "partner_motion"
  | "mixed_identity"
  | "multi_environment"
  | "extended_retention_or_trust_review"
  | "ai_shield_primary";

const QUALIFICATION_REASON_LABELS: Record<DemoQualificationReason, string> = {
  partner_motion: "Partner-led or managed-tenant delivery",
  mixed_identity: "Mixed or undecided identity architecture",
  multi_environment: "More than one core cloud environment in the first rollout",
  extended_retention_or_trust_review: "Extended retention, archive, or trust-review requirements",
  ai_shield_primary: "AI Shield is the primary buying reason",
};

function deriveGuidedReviewReasons({
  motion,
  identityProfile,
  rolloutScope,
  retentionProfile,
  aiShieldFit,
}: {
  motion: "standard" | "partner";
  identityProfile: DemoIdentityProfile;
  rolloutScope: DemoRolloutScope;
  retentionProfile: DemoRetentionProfile;
  aiShieldFit: DemoAIShieldFit;
}): DemoQualificationReason[] {
  const reasons: DemoQualificationReason[] = [];

  if (motion === "partner") {
    reasons.push("partner_motion");
  }
  if (identityProfile === "mixed") {
    reasons.push("mixed_identity");
  }
  if (rolloutScope === "multi_environment") {
    reasons.push("multi_environment");
  }
  if (retentionProfile === "extended_or_archive") {
    reasons.push("extended_retention_or_trust_review");
  }
  if (aiShieldFit === "primary") {
    reasons.push("ai_shield_primary");
  }

  return reasons;
}

function splitFullName(fullName: string) {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return null;
  }

  return {
    firstName: parts[0],
    lastName: parts.length > 1 ? parts.slice(1).join(" ") : parts[0],
  };
}

export function DemoRequestForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [size, setSize] = useState("26-100 employees");
  const [planInterest, setPlanInterest] = useState<MarketingPlanKey | "">("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [demoMotion, setDemoMotion] = useState<"partner" | null>(null);
  const [identityProfile, setIdentityProfile] =
    useState<DemoIdentityProfile>("microsoft_entra");
  const [rolloutScope, setRolloutScope] =
    useState<DemoRolloutScope>("single_environment");
  const [retentionProfile, setRetentionProfile] =
    useState<DemoRetentionProfile>("standard");
  const [aiShieldFit, setAiShieldFit] = useState<DemoAIShieldFit>("none");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const planParam = params.get("plan");
    const motionParam = params.get("motion");
    if (isMarketingPlanKey(planParam)) {
      setPlanInterest(planParam);
    }
    if (motionParam === "partner") {
      setDemoMotion("partner");
      setNotes((current) =>
        current.length > 0
          ? current
          : "Interested in partner / MSP workflow, delivery modes, and managed-tenant operations."
      );
    }
  }, []);

  const motion = demoMotion === "partner" ? "partner" : "standard";
  const guidedReviewReasons = deriveGuidedReviewReasons({
    motion,
    identityProfile,
    rolloutScope,
    retentionProfile,
    aiShieldFit,
  });
  const recommendedPath =
    guidedReviewReasons.length > 0 ? "guided_review" : "standard_launch_path";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);

    const parsedName = splitFullName(name);
    if (!parsedName) {
      setError("Please enter your full name.");
      return;
    }

    setSubmitting(true);

    try {
      const response = await createDemoRequest({
        email,
        company_name: company,
        first_name: parsedName.firstName,
        last_name: parsedName.lastName,
        company_size: size,
        notes,
        plan_tier: planInterest || undefined,
        source: demoMotion === "partner" ? "demo_page_partner_form" : "demo_page_form",
        motion,
        identity_profile: identityProfile,
        rollout_scope: rolloutScope,
        retention_profile: retentionProfile,
        ai_shield_fit: aiShieldFit,
      });

      trackMarketingEvent("marketing_demo_submit", {
        source: demoMotion === "partner" ? "demo_page_partner_form" : "demo_page_form",
        companySize: size,
        planInterest: planInterest || "unspecified",
        motion: demoMotion || "standard",
        lead_id: response.lead_id,
        recommendedPath,
        result: "success",
      });

      setSuccessMessage(response.message);
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "Unable to submit your demo request. Please try again.";
      setError(message);

      trackMarketingEvent("marketing_demo_submit", {
        source: demoMotion === "partner" ? "demo_page_partner_form" : "demo_page_form",
        companySize: size,
        planInterest: planInterest || "unspecified",
        motion: demoMotion || "standard",
        recommendedPath,
        result: "error",
        errorMessage: message,
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (successMessage) {
    return (
      <div className="space-y-5 rounded-xl border border-emerald-700/50 bg-emerald-950/40 p-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-300 mb-2">
            Request received
          </p>
          <h2 className="text-2xl font-semibold text-text-main">
            We have your demo request.
          </h2>
          <p className="mt-3 text-sm leading-6 text-text-main/80">
            {successMessage}
          </p>
        </div>
        <div className="rounded-2xl border border-emerald-800/60 bg-bg/40 p-4 text-sm leading-6 text-text-muted">
          We will follow up at <span className="font-medium text-text-main">{email}</span>. If you
          want to move faster, you can start guided onboarding now and still keep the demo on the calendar.
        </div>
        <div className="rounded-2xl border border-emerald-800/60 bg-bg/40 p-4 text-sm leading-6 text-text-muted">
          {recommendedPath === "guided_review" ? (
            <>
              This request was tagged for a guided review because of your rollout shape:
              <span className="block mt-2 text-text-main">
                {guidedReviewReasons.map((reason) => QUALIFICATION_REASON_LABELS[reason]).join("; ")}
              </span>
            </>
          ) : (
            "This request fits the standard launch path, so the follow-up can stay anchored to the default onboarding motion."
          )}
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href={planInterest ? `/signup?plan=${planInterest}` : "/signup"}
            className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Start guided onboarding
          </Link>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            Submit another request
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-border bg-bg-alt/90 p-6">
      {demoMotion === "partner" ? (
        <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-sm leading-6 text-text-main/80">
          This request is tagged for a partner / MSP conversation so the follow-up can focus on
          managed-tenant workflows, delivery modes, and delegated response guardrails.
        </div>
      ) : (
        <div className="rounded-2xl border border-border-muted bg-bg/40 px-4 py-3 text-sm leading-6 text-text-muted">
          Standard demos lead with the default launch path: `Protect + Defend`, AWS, and Microsoft
          365 / Entra first. If your rollout needs partner delivery, unusual retention, complex
          multi-environment scope, or AI Shield as the primary buying driver, we will scope it as
          a guided review instead of a generic self-serve fit.
        </div>
      )}
      <div>
        <label htmlFor="demo-name" className="block text-sm text-text-muted mb-1">
          Name
        </label>
        <input
          id="demo-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
          placeholder="Jane Doe"
        />
      </div>
      <div>
        <label htmlFor="demo-email" className="block text-sm text-text-muted mb-1">
          Work email
        </label>
        <input
          id="demo-email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          type="email"
          required
          className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
          placeholder="you@company.com"
        />
      </div>
      <div>
        <label htmlFor="demo-company" className="block text-sm text-text-muted mb-1">
          Company name
        </label>
        <input
          id="demo-company"
          value={company}
          onChange={(event) => setCompany(event.target.value)}
          required
          className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
          placeholder="Company Inc."
        />
      </div>
      <details className="group">
        <summary className="cursor-pointer text-sm text-text-muted/70 hover:text-text-main/80 transition-colors">
          Tell us more (optional)
        </summary>
        <div className="mt-3 space-y-4">
          <div>
            <label htmlFor="demo-size" className="block text-sm text-text-muted mb-1">
              Company size
            </label>
            <select
              id="demo-size"
              value={size}
              onChange={(event) => setSize(event.target.value)}
              className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
            >
              <option>1-25 employees</option>
              <option>26-100 employees</option>
              <option>101-250 employees</option>
              <option>251-1000 employees</option>
              <option>1000+ employees</option>
            </select>
          </div>
          <div>
            <label htmlFor="demo-plan" className="block text-sm text-text-muted mb-1">
              Package focus
            </label>
            <select
              id="demo-plan"
              value={planInterest}
              onChange={(event) => setPlanInterest(event.target.value as MarketingPlanKey | "")}
              className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
            >
              <option value="">Not sure yet</option>
              {marketingPlans.map((plan) => (
                <option key={plan.key} value={plan.key}>
                  {plan.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="demo-notes" className="block text-sm text-text-muted mb-1">
              What do you want to see?
            </label>
            <textarea
              id="demo-notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
              className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
              placeholder="AWS + Microsoft 365 onboarding, pricing, response workflow, trust artifacts, AI Shield add-on scope..."
            />
          </div>
          <div>
            <label htmlFor="demo-identity" className="block text-sm text-text-muted mb-1">
              Identity path
            </label>
            <select
              id="demo-identity"
              value={identityProfile}
              onChange={(event) =>
                setIdentityProfile(event.target.value as DemoIdentityProfile)
              }
              className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
            >
              <option value="microsoft_entra">Microsoft 365 / Entra</option>
              <option value="google_workspace">Google Workspace</option>
              <option value="okta">Okta</option>
              <option value="mixed">Mixed or not sure yet</option>
            </select>
          </div>
          <div>
            <label htmlFor="demo-rollout-scope" className="block text-sm text-text-muted mb-1">
              Rollout scope
            </label>
            <select
              id="demo-rollout-scope"
              value={rolloutScope}
              onChange={(event) =>
                setRolloutScope(event.target.value as DemoRolloutScope)
              }
              className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
            >
              <option value="single_environment">One core cloud environment first</option>
              <option value="multi_environment">Multiple core environments in the first rollout</option>
            </select>
          </div>
          <div>
            <label htmlFor="demo-retention" className="block text-sm text-text-muted mb-1">
              Retention and trust needs
            </label>
            <select
              id="demo-retention"
              value={retentionProfile}
              onChange={(event) =>
                setRetentionProfile(event.target.value as DemoRetentionProfile)
              }
              className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
            >
              <option value="standard">Standard package assumptions</option>
              <option value="extended_or_archive">Extended retention, archive, or heavier trust review</option>
            </select>
          </div>
          <div>
            <label htmlFor="demo-ai-shield-fit" className="block text-sm text-text-muted mb-1">
              AI Shield interest
            </label>
            <select
              id="demo-ai-shield-fit"
              value={aiShieldFit}
              onChange={(event) => setAiShieldFit(event.target.value as DemoAIShieldFit)}
              className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
            >
              <option value="none">Not part of this evaluation</option>
              <option value="add_on">Interested as an add-on</option>
              <option value="primary">Primary buying reason</option>
            </select>
          </div>
          <div
            className={`rounded-2xl border px-4 py-3 text-sm leading-6 ${
              recommendedPath === "guided_review"
                ? "border-cyan-500/20 bg-cyan-500/10 text-text-main/80"
                : "border-emerald-700/40 bg-emerald-950/30 text-text-main/80"
            }`}
          >
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Qualification result
            </p>
            {recommendedPath === "guided_review" ? (
              <>
                <p className="mt-2">
                  This looks like a guided review instead of the standard launch path.
                </p>
                <ul className="mt-2 space-y-1 text-text-muted">
                  {guidedReviewReasons.map((reason) => (
                    <li key={reason}>• {QUALIFICATION_REASON_LABELS[reason]}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="mt-2 text-text-muted">
                This still fits the standard launch path: direct buyer motion, default rollout shape,
                and AI as an optional add-on rather than the primary scope.
              </p>
            )}
          </div>
        </div>
      </details>
      {error ? (
        <div className="rounded-2xl border border-rose-700/50 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}
      <button
        type="submit"
        disabled={submitting}
        className="inline-flex w-full items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
      >
        {submitting ? "Submitting request..." : "Request a guided demo"}
      </button>
      <p className="text-xs leading-5 text-text-muted/70">
        We store your request in SentinelGrid so the team can follow up with a concrete walkthrough.
      </p>
    </form>
  );
}
