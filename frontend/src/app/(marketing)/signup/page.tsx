"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { HelpButton } from "@/components/HelpButton";
import { Logo } from "@/components/Logo";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createLead, updateLead } from "@/lib/api/leads";
import { calculatePrice, createCheckoutSession, type PricingInfo } from "@/lib/api/payment";
import {
  defaultMarketingPlanKey,
  getMarketingPlan,
  isMarketingPlanKey,
  marketingPlans,
  type MarketingPlanKey,
} from "@/lib/marketing/packages";
import {
  applyPlanDefaults,
  planIncludesCompliance,
  type ServicesSelected,
} from "@/lib/product/catalog";
import {
  recordPaymentStarted,
  recordPaymentViewed,
  recordSignupLeadCreated,
  recordSignupStarted,
} from "@/lib/onboarding/metrics";
import { launchWorkflowSteps } from "@/lib/marketing/launchWorkflow";

type Step = 1 | 2 | 3;  // Step 1: Account, Step 2: Choose path, Step 3: Payment

export default function SignupPage() {
  const router = useRouter();
  const [initialStep, setInitialStep] = useState<Step>(1);

  useEffect(() => {
    recordSignupStarted({ source: "signup_page" });
  }, []);

  // Check for step parameter in URL (for resuming incomplete signup)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const stepParam = params.get('step');
      if (stepParam) {
        const stepNum = parseInt(stepParam, 10);
        if (stepNum >= 1 && stepNum <= 3) {
          setInitialStep(stepNum as Step);
        }
      }
    }
  }, []);

  const [step, setStep] = useState<Step>(initialStep);

  // Update step when initialStep changes (from URL param)
  useEffect(() => {
    setStep(initialStep);
  }, [initialStep]);

  const next = () => setStep((s) => (s < 3 ? ((s + 1) as Step) : s));
  const back = () => setStep((s) => (s > 1 ? ((s - 1) as Step) : s));

  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-3xl bg-bg-alt/90 border border-border rounded-2xl p-6 md:p-8 shadow-2xl">
          <div className="flex items-center gap-2.5 mb-6">
            <Logo className="w-6 h-6" />
            <span className="font-semibold tracking-wide">
              Sentinel<span className="text-cyan-400">Grid</span>
            </span>
          </div>
          <h1 className="text-2xl font-semibold mb-2">Start guided onboarding with SentinelGrid</h1>
          <p className="text-sm text-text-muted mb-6">
            Create your account and start the standard launch path: connect identity, connect
            cloud, decide whether endpoint coverage is part of the first rollout, then work from
            one prioritized queue with a guided action pack. You&apos;ll see your first security
            insights quickly without stitching together extra tools first.
          </p>

          <div className="mb-6 rounded-xl border border-border bg-bg/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Standard launch path
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-5">
              {launchWorkflowSteps.map((item) => (
                <div key={item.id} className="rounded-xl border border-border bg-bg-alt/80 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    {item.stepLabel}
                  </p>
                  <p className="mt-2 text-sm font-semibold text-text-main">{item.title}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Step indicator */}
          <div className="flex items-center gap-2 mb-6 text-xs text-text-muted/70">
            <StepPill active={step === 1} completed={step > 1} stepNumber={1}>Account</StepPill>
            <span className="text-slate-600">→</span>
            <StepPill active={step === 2} completed={step > 2} stepNumber={2}>Choose plan</StepPill>
            {step >= 3 && (
              <>
                <span className="text-slate-600">→</span>
                <StepPill active={step === 3} completed={false} stepNumber={3}>Payment</StepPill>
              </>
            )}
          </div>

          {step === 1 && <StepAccount onNext={next} />}
          {step === 2 && <StepChoosePath onBack={back} onNext={next} />}
          {step === 3 && <StepPayment onBack={() => setStep(2 as Step)} />}
        </div>
      </div>
      <HelpButton />
    </main>
  );
}

function StepPill({
  active,
  completed,
  stepNumber,
  children,
}: {
  active: boolean;
  completed: boolean;
  stepNumber: number;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${
        active
          ? "border-cyan-400 bg-cyan-400/10 text-cyan-300"
          : completed
          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
          : "border-border-muted bg-bg-alt/60"
      }`}
    >
      {completed ? (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <span className="text-[11px] font-semibold">{stepNumber}</span>
      )}
      {children}
    </span>
  );
}

function PasswordStrength({ password }: { password: string }) {
  const checks = [
    { label: "8+ characters", met: password.length >= 8 },
    { label: "Uppercase", met: /[A-Z]/.test(password) },
    { label: "Lowercase", met: /[a-z]/.test(password) },
    { label: "Number", met: /[0-9]/.test(password) },
  ];
  const metCount = checks.filter((c) => c.met).length;
  const barColor =
    metCount <= 1 ? "bg-red-500" : metCount <= 2 ? "bg-amber-500" : metCount <= 3 ? "bg-yellow-400" : "bg-emerald-500";

  if (!password) {
    return <p className="text-xs text-text-muted/70 mt-1">Must be at least 8 characters with uppercase, lowercase, and number</p>;
  }

  return (
    <div className="mt-1.5 space-y-1.5">
      <div className="flex gap-1">
        {checks.map((_, i) => (
          <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i < metCount ? barColor : "bg-slate-700"}`} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        {checks.map((check) => (
          <span key={check.label} className={`text-[11px] ${check.met ? "text-emerald-400" : "text-text-main0"}`}>
            {check.met ? "✓" : "○"} {check.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function StepAccount({
  onNext
}: {
  onNext: () => void;
}) {
  const [email, setEmail] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [employeeCount, setEmployeeCount] = useState<number | null>(null);
  const [planTier, setPlanTier] = useState<MarketingPlanKey>(defaultMarketingPlanKey);
  const [complianceRequired, setComplianceRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Derived flags
  useEffect(() => {
    setComplianceRequired(planTier === 'protect_defend_comply');
  }, [planTier]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const planParam = params.get('plan');
    if (isMarketingPlanKey(planParam)) {
      setPlanTier(planParam);
    }
  }, []);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Parse full name into first and last
      const nameParts = fullName.trim().split(/\s+/).filter(part => part.length > 0);
      if (nameParts.length === 0) {
        setError('Please enter your full name');
        setLoading(false);
        return;
      }
      const firstName = nameParts[0];
      const lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : nameParts[0]; // Use first name as last name if only one name provided

      // Validate employee count
      if (!employeeCount || employeeCount < 1) {
        setError('Please select your company size');
        setLoading(false);
        return;
      }

      // Call leads API (creates lead, not account)
      const servicesPayload = applyPlanDefaults(planTier, { cloud: true });
      const response = await createLead({
        company_name: companyName,
        email: email,
        password: password,
        first_name: firstName,
        last_name: lastName,
        user_count: employeeCount,
        compliance_required: planIncludesCompliance(planTier),
        plan_tier: planTier,
        tenant_slug: tenantSlug || undefined,
        services_selected: servicesPayload,
      });

      if (response.success) {
        // Store lead_id for payment step
        localStorage.setItem('lead_id', response.lead_id);
        
        // Store email for payment success page (password handled via session)
        localStorage.setItem('signup_email', email);
        sessionStorage.setItem('signup_session_token', response.session_token || '');
        
        // Store signup data for payment step
        localStorage.setItem('signup_user_count', employeeCount.toString());
        localStorage.setItem('signup_compliance_required', planIncludesCompliance(planTier).toString());
        localStorage.setItem('signup_plan_tier', planTier);
        localStorage.setItem('signup_pricing', JSON.stringify(response.pricing));
        localStorage.setItem('signup_services', JSON.stringify(servicesPayload));
        recordSignupLeadCreated({
          leadId: response.lead_id,
          planTier,
          employeeCount,
          servicesSelected: servicesPayload,
        });
        
        // Always proceed to next step (payment) after successful lead creation
        onNext();
      }
    } catch (err: any) {
      // Extract error message properly
      let errorMessage = 'Signup failed. Please try again.';
      
      // Log the full error for debugging
      console.error('Signup error caught:', {
        error: err,
        type: typeof err,
        isError: err instanceof Error,
        message: err?.message,
        detail: err?.detail,
        stringified: JSON.stringify(err, null, 2)
      });
      // Also log the error object directly for better visibility
      console.error('Full error object:', err);
      
      if (err instanceof Error) {
        errorMessage = err.message || err.toString();
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else if (err?.message) {
        errorMessage = typeof err.message === 'string' ? err.message : String(err.message);
      } else if (err?.detail) {
        if (typeof err.detail === 'string') {
          errorMessage = err.detail;
        } else if (Array.isArray(err.detail)) {
          errorMessage = err.detail.map((e: any) => {
            if (typeof e === 'string') return e;
            return e.msg || e.message || JSON.stringify(e);
          }).join('; ');
        } else {
          errorMessage = JSON.stringify(err.detail);
        }
      } else {
        // Last resort: try to stringify the error
        try {
          errorMessage = JSON.stringify(err);
        } catch {
          errorMessage = String(err) || 'Signup failed. Please try again.';
        }
      }
      
      // Ensure we have a valid string - convert to string if needed
      if (!errorMessage || typeof errorMessage !== 'string') {
        errorMessage = 'Signup failed. Please check your input and try again.';
      }
      
      // Force conversion to string and check for [object Object]
      let finalErrorMessage: string;
      if (typeof errorMessage === 'string') {
        finalErrorMessage = errorMessage;
      } else {
        try {
          finalErrorMessage = JSON.stringify(errorMessage);
        } catch {
          finalErrorMessage = String(errorMessage);
        }
      }
      
      // Final validation - ensure it's not [object Object] or empty
      if (!finalErrorMessage || 
          finalErrorMessage === '[object Object]' || 
          finalErrorMessage === '{}' ||
          finalErrorMessage === 'null' ||
          finalErrorMessage === 'undefined' ||
          finalErrorMessage.trim() === '') {
        finalErrorMessage = 'Signup failed. Please check your input and try again.';
      }
      
      setError(finalErrorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
          {typeof error === 'string' ? error : String(error)}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label htmlFor="email" className="block text-xs text-text-muted mb-1">
            Work email
          </label>
          <input
            id="email"
            required
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-border-muted bg-bg/60 px-3 py-2 text-sm text-text-main/80"
            placeholder="you@company.com"
            autoComplete="email"
          />
        </div>
        <div>
          <label htmlFor="company" className="block text-xs text-text-muted mb-1">
            Company name
          </label>
          <input
            id="company"
            required
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="w-full rounded-lg border border-border-muted bg-bg/60 px-3 py-2 text-sm text-text-main/80"
            placeholder="Company Inc."
          />
        </div>
        <div className="md:col-span-2">
          <details className="group">
            <summary className="cursor-pointer text-xs text-text-muted/70 hover:text-text-main/80 transition-colors">
              Customize your workspace URL (optional)
            </summary>
            <div className="mt-2">
              <label htmlFor="tenantSlug" className="block text-xs text-text-muted mb-1">
                Workspace slug
              </label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-main0">app.sentinelgrid.ai/</span>
                <input
                  id="tenantSlug"
                  type="text"
                  value={tenantSlug}
                  onChange={(e) => setTenantSlug(e.target.value)}
                  className="flex-1 rounded-lg border border-border-muted bg-bg/60 px-3 py-2 text-sm text-text-main/80"
                  placeholder="acme-co"
                  pattern="[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?"
                  title="3-40 chars, lowercase letters/numbers/hyphen, no leading/trailing hyphen"
                />
              </div>
              <p className="text-[11px] text-text-main0 mt-1">We will generate one from your company name if you skip this.</p>
            </div>
          </details>
        </div>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label htmlFor="name" className="block text-xs text-text-muted mb-1">
            Your name
          </label>
          <input
            id="name"
            required
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-border-muted bg-bg/60 px-3 py-2 text-sm text-text-main/80"
            placeholder="Jane Doe"
            autoComplete="name"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-xs text-text-muted mb-1">
            Password
          </label>
          <input
            id="password"
            required
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-border-muted bg-bg/60 px-3 py-2 text-sm text-text-main/80"
            placeholder="••••••••"
            autoComplete="new-password"
            minLength={8}
          />
          <PasswordStrength password={password} />
        </div>
      </div>
      
      <div className="pt-4 border-t border-border">
        <div className="mb-4">
          <label htmlFor="employeeCount" className="block text-xs text-text-muted mb-1">
            Company size <span className="text-red-400">*</span>
          </label>
          <select
            id="employeeCount"
            required
            value={employeeCount || ''}
            onChange={(e) => setEmployeeCount(e.target.value ? parseInt(e.target.value) : null)}
            className="w-full rounded-lg border border-border-muted bg-bg/60 px-3 py-2 text-sm text-text-main/80"
          >
            <option value="">Select company size...</option>
            <option value="1">1-5 employees</option>
            <option value="6">6-25 employees</option>
            <option value="26">26-100 employees</option>
            <option value="101">101-250 employees</option>
            <option value="251">251-1000 employees</option>
            <option value="1001">1000+ employees</option>
          </select>
        </div>
      </div>
      <div className="flex items-center gap-2 pt-2">
        <input type="checkbox" id="terms" required className="rounded" />
        <label htmlFor="terms" className="text-xs text-text-muted/70">
          I agree to the{" "}
          <Link href="/terms" className="text-cyan-400 hover:underline">
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="text-cyan-400 hover:underline">
            Privacy Policy
          </Link>
        </label>
      </div>
      <button
        type="submit"
        disabled={loading}
        className="mt-4 w-full inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Creating account...' : 'Create account'}
      </button>
      <p className="mt-3 text-center text-xs text-text-main0">
        You can explore the platform free before choosing a plan.
      </p>
    </form>
  );
}

function StepChoosePath({ onBack, onNext }: { onBack: () => void; onNext: () => void }) {
  const router = useRouter();
  const [planTier, setPlanTier] = useState<MarketingPlanKey>(defaultMarketingPlanKey);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const planParam = params.get('plan');
    if (isMarketingPlanKey(planParam)) {
      setPlanTier(planParam);
    }
    const stored = localStorage.getItem('signup_plan_tier');
    if (!planParam && isMarketingPlanKey(stored)) {
      setPlanTier(stored);
    }
  }, []);

  const selectedPlan = getMarketingPlan(planTier);

  const handleContinueToPayment = async () => {
    if (saving) {
      return;
    }

    const leadId = localStorage.getItem('lead_id');
    const provisioningToken = sessionStorage.getItem('signup_session_token');

    if (!leadId || !provisioningToken) {
      setError('Missing signup session. Please start over.');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const storedServices = (() => {
        const raw = localStorage.getItem('signup_services');
        if (!raw) return {};
        try {
          return JSON.parse(raw) as ServicesSelected;
        } catch {
          return {};
        }
      })();

      const servicesPayload = applyPlanDefaults(planTier, storedServices);
      const response = await updateLead(leadId, provisioningToken, {
        plan_tier: planTier,
        compliance_required: planIncludesCompliance(planTier),
        services_selected: servicesPayload,
      });

      localStorage.setItem('signup_plan_tier', planTier);
      localStorage.setItem('signup_compliance_required', planIncludesCompliance(planTier).toString());
      localStorage.setItem('signup_services', JSON.stringify(servicesPayload));
      localStorage.setItem('signup_pricing', JSON.stringify(response.pricing));
      if (response.session_token) {
        sessionStorage.setItem('signup_session_token', response.session_token);
      }

      onNext();
    } catch (err: any) {
      setError(err?.message || 'Failed to update your package selection');
    } finally {
      setSaving(false);
    }
  };

  const handleExploreFree = () => {
    const email = localStorage.getItem('signup_email') || '';
    router.push(email ? `/login?email=${encodeURIComponent(email)}` : '/login');
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold mb-1">Your account is ready</h2>
        <p className="text-sm text-text-muted">
          Choose a plan to unlock all features, or explore the platform free first.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-3">
        {marketingPlans.map((plan) => (
          <button
            type="button"
            key={plan.key}
            onClick={() => setPlanTier(plan.key)}
            className={`text-left rounded-xl border-2 p-4 transition-all ${
              planTier === plan.key
                ? 'border-cyan-500 bg-cyan-500/10 shadow-lg shadow-cyan-500/20'
                : 'border-border-muted bg-bg-alt/60 hover:border-cyan-500/60'
            }`}
          >
            {plan.badge && (
              <span className="inline-flex items-center px-2 py-1 text-[10px] font-semibold rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 text-white mb-2">
                {plan.badge}
              </span>
            )}
            <div className="text-sm font-semibold text-text-main">{plan.name}</div>
            <div className="text-xs text-text-muted/70">{plan.subtitle}</div>
            <div className="mt-3 text-[11px] font-medium uppercase tracking-[0.14em] text-cyan-300">
              {plan.priceLabel}
            </div>
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-border bg-bg/60 p-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Selected package
            </p>
            <h5 className="mt-1 text-sm font-semibold text-text-main">{selectedPlan.name}</h5>
            <p className="mt-2 text-xs leading-5 text-text-muted/70">{selectedPlan.summary}</p>
          </div>
          <div className="text-left md:text-right">
            <p className="text-sm font-semibold text-text-main">{selectedPlan.priceLabel}</p>
            <p className="text-xs text-text-main0">{selectedPlan.annualLabel}</p>
          </div>
        </div>
        <ul className="mt-4 grid gap-2 md:grid-cols-2">
          {selectedPlan.included.slice(0, 4).map((item) => (
            <li key={item} className="flex gap-2 text-xs text-text-muted">
              <span className="mt-0.5 text-cyan-400">&#10003;</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="flex flex-col gap-3 pt-2">
        <button
          type="button"
          onClick={() => { void handleContinueToPayment(); }}
          disabled={saving}
          className="w-full inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Updating package...' : 'Continue to payment'}
        </button>
        <button
          type="button"
          onClick={handleExploreFree}
          className="w-full inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-medium border border-border-muted text-text-main/80 hover:border-cyan-400 transition-colors"
        >
          Explore free first
        </button>
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-text-main0 hover:text-text-muted transition-colors"
        >
          &larr; Back
        </button>
      </div>
    </div>
  );
}

function StepPayment({ onBack }: { onBack: () => void }) {
  const router = useRouter();
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pricing, setPricing] = useState<PricingInfo | null>(null);
  const [processingPayment, setProcessingPayment] = useState(false);
  const [signupData, setSignupData] = useState<{
    leadId: string;
    userCount: number;
    complianceRequired: boolean;
    planTier?: MarketingPlanKey;
    services?: ServicesSelected;
  } | null>(null);
  const [planTier, setPlanTier] = useState<MarketingPlanKey>(defaultMarketingPlanKey);

  useEffect(() => {
    recordPaymentViewed({ source: "signup_payment_step", planTier });
  }, [planTier]);

  useEffect(() => {
    const leadId = localStorage.getItem('lead_id');
    const userCount = parseInt(localStorage.getItem('signup_user_count') || '26', 10);
    const storedPlanTier = localStorage.getItem('signup_plan_tier');
    const planTierStored = isMarketingPlanKey(storedPlanTier)
      ? storedPlanTier
      : defaultMarketingPlanKey;
    const complianceRequired = planIncludesCompliance(planTierStored);
    const pricingStr = localStorage.getItem('signup_pricing');
    const servicesStr = localStorage.getItem('signup_services');
    const servicesParsed = servicesStr ? JSON.parse(servicesStr) : undefined;
    
    if (!leadId) {
      setError('Missing signup data. Please start over.');
      return;
    }
      setSignupData({
        leadId,
        userCount,
        complianceRequired,
        planTier: planTierStored,
        services: servicesParsed,
      });
    setPlanTier(planTierStored);
    
    // Calculate pricing with new API
    if (userCount && (complianceRequired !== undefined)) {
      calculatePricing(userCount, planTierStored, complianceRequired, billingPeriod, servicesParsed);
    } else if (pricingStr) {
      // Use stored pricing if available
      try {
        const storedPricing = JSON.parse(pricingStr);
        setPricing(storedPricing);
      } catch (e) {
        console.error('Error parsing stored pricing:', e);
      }
    }
  }, []);

  const calculatePricing = async (
    userCount: number,
    selectedPlanTier: MarketingPlanKey,
    compliance: boolean,
    period: 'monthly' | 'yearly',
    services?: ServicesSelected
  ) => {
    try {
      setLoading(true);
      const pricingInfo = await calculatePrice({
        user_count: userCount,
        compliance_required: compliance,
        plan_tier: selectedPlanTier,
        billing_period: period,
        services_selected: services,
      });
      setPricing(pricingInfo);
    } catch (err: any) {
      setError(err.message || 'Failed to calculate pricing');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (signupData && billingPeriod) {
      const servicesStored = localStorage.getItem('signup_services');
      const servicesParsed = servicesStored ? JSON.parse(servicesStored) : undefined;
      calculatePricing(
        signupData.userCount,
        signupData.planTier || defaultMarketingPlanKey,
        signupData.complianceRequired,
        billingPeriod,
        servicesParsed
      );
    }
  }, [billingPeriod, signupData]);

  const handlePayment = async () => {
    if (!signupData || !pricing) return;
    recordPaymentStarted({
      planTier,
      billingPeriod,
      requiresSalesContact: pricing.requires_sales_contact || pricing.total === null,
    });
    if (pricing.requires_sales_contact || pricing.total === null) {
      router.push(`/demo?plan=${planTier}`);
      return;
    }
    if (pricing.total === 0) {
      router.push('/dashboard');
      return;
    }
    try {
      setProcessingPayment(true);
      setError(null);
      const provisioningToken = sessionStorage.getItem('signup_session_token');
      if (!provisioningToken) {
        throw new Error('Missing signup provisioning token');
      }
      const successUrl = `${window.location.origin}/signup/payment-success?session_id={CHECKOUT_SESSION_ID}&lead_id=${signupData.leadId}`;
      const cancelUrl = `${window.location.origin}/signup?step=3`;
      const checkout = await createCheckoutSession({
        lead_id: signupData.leadId,
        provisioning_token: provisioningToken,
        billing_period: billingPeriod,
        success_url: successUrl,
        cancel_url: cancelUrl,
        services_selected: signupData.services || {},
      });
      
      // Handle dev mode (bypasses Stripe)
      if (checkout.dev_mode) {
        // In dev mode, checkout.url is the success URL with session_id already replaced
        window.location.href = checkout.url || successUrl.replace('{CHECKOUT_SESSION_ID}', checkout.session_id || '');
      } else if (checkout.url) {
        // Production: redirect to Stripe checkout
        window.location.href = checkout.url;
      } else {
        throw new Error('Failed to create checkout session');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to start payment process');
      setProcessingPayment(false);
    }
  };

  if (!signupData) {
    return <div className="space-y-4"><p className="text-sm text-text-muted">Loading payment information...</p></div>;
  }

  const selectedPlan = getMarketingPlan(planTier);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Complete your subscription</h2>
        <p className="text-sm text-text-muted">
          You selected <span className="font-semibold text-cyan-400">{selectedPlan.name}</span>. Choose billing and confirm.
        </p>
      </div>
      <div className="rounded-xl border border-border-muted bg-bg-alt/70 p-4 text-sm text-text-muted">
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-text-main">Plan</span>
          <span className="px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-xs">
            {selectedPlan.name}
          </span>
        </div>
        <p className="text-xs text-text-muted/70">{selectedPlan.subtitle}</p>
        <ul className="mt-3 grid gap-2 md:grid-cols-2">
          {selectedPlan.included.slice(0, 4).map((item) => (
            <li key={item} className="flex gap-2 text-xs text-text-muted">
              <span className="mt-0.5 text-cyan-400">✓</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex items-center gap-4 p-4 bg-bg-alt/60 rounded-lg border border-border-muted">
        <button type="button" onClick={() => setBillingPeriod('monthly')}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
            billingPeriod === 'monthly' ? 'bg-cyan-400 text-slate-950' : 'bg-slate-700 text-text-muted hover:bg-slate-600'
          }`}>Monthly</button>
        <button type="button" onClick={() => setBillingPeriod('yearly')}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors relative ${
            billingPeriod === 'yearly' ? 'bg-cyan-400 text-slate-950' : 'bg-slate-700 text-text-muted hover:bg-slate-600'
          }`}>
          Yearly<span className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-0.5 rounded-full">Save 17%</span>
        </button>
      </div>
      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-text-muted/70">Calculating pricing...</p>
        </div>
      ) : pricing ? (
        <div className="space-y-4">
          <div className="bg-bg-alt/60 rounded-lg border border-border-muted p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-text-muted">Base Plan</span>
              <span className="text-lg font-semibold text-cyan-400">
                {pricing.base_price !== null ? `$${(pricing.base_price / 100).toFixed(2)}` : 'Custom'}/{billingPeriod === 'monthly' ? 'mo' : 'yr'}
              </span>
            </div>
            <p className="text-xs text-text-muted/70">
              {selectedPlan.name} package
            </p>
          </div>
          {pricing.addons.length > 0 && (
            <div className="bg-bg-alt/60 rounded-lg border border-border-muted p-4">
              <h3 className="text-sm font-semibold text-text-main/80 mb-3">Add-ons</h3>
              <div className="space-y-2">
                {pricing.addons.map((addon, idx) => (
                  <div key={idx} className="flex justify-between items-center">
                    <span className="text-sm text-text-muted">{addon.name}</span>
                    <span className="text-sm font-medium text-cyan-400">{addon.display}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="bg-gradient-to-r from-cyan-500/20 to-cyan-400/20 rounded-lg border border-cyan-400/30 p-4">
            <div className="flex justify-between items-center">
              <span className="text-lg font-semibold text-text-main/80">Total</span>
              <div className="text-right">
                <div className="text-2xl font-bold text-cyan-400">{pricing.display}</div>
                {billingPeriod === 'yearly' && pricing.discount > 0 && (
                  <div className="text-xs text-green-400 mt-1">Save ${(pricing.discount / 100).toFixed(2)} per year</div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">{error}</div>
      )}
      <div className="flex justify-between pt-4">
        <button type="button" onClick={onBack} className="text-xs text-text-muted hover:text-text-main">← Back</button>
        <button type="button" onClick={handlePayment} disabled={loading || processingPayment || !pricing}
          className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-semibold bg-gradient-to-r from-cyan-400 to-cyan-500 text-slate-950 hover:brightness-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20">
          {processingPayment ? (
            <> <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-slate-950 mr-2"></div> Processing... </>
          ) : pricing?.requires_sales_contact ? 'Talk to sales' : pricing?.total === 0 ? 'Complete setup' : `Pay ${pricing?.display || ''}`}
        </button>
      </div>
      <div className="flex items-center justify-center gap-2 text-xs text-text-muted/70 pt-4 border-t border-border">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <span>Secure payment powered by Stripe</span>
      </div>
    </div>
  );
}
