/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import { useState, useMemo, useEffect } from "react";
import { Header } from "@/components/Header";
import { Logo } from "@/components/Logo";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signup as signupAPI } from "@/lib/api/auth";
import { calculatePrice, createCheckoutSession, handlePaymentSuccess, type PricingInfo } from "@/lib/api/payment";
import { login as loginAPI } from "@/lib/api/auth";

type Step = 1 | 2 | 3 | 4 | 5;

export default function SignupPage() {
  const router = useRouter();
  const [initialStep, setInitialStep] = useState<Step>(1);

  // Check for step parameter in URL (for resuming incomplete signup)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const stepParam = params.get('step');
      if (stepParam) {
        const stepNum = parseInt(stepParam, 10);
        if (stepNum >= 1 && stepNum <= 5) {
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

  const next = () => setStep((s) => (s < 5 ? ((s + 1) as Step) : s));
  const back = () => setStep((s) => (s > 1 ? ((s - 1) as Step) : s));

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-3xl bg-slate-900/70 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl">
          <div className="flex items-center gap-2.5 mb-6">
            <Logo className="w-6 h-6" />
            <span className="font-semibold tracking-wide">
              Sentinel<span className="text-cyan-400">Grid</span>
            </span>
          </div>
          <h1 className="text-2xl font-semibold mb-2">Get started with SentinelGrid</h1>
          <p className="text-sm text-slate-300 mb-6">
            Create your account and connect your environment. You&apos;ll see your
            first security insights within a day.
          </p>

          {/* Step indicator */}
          <div className="flex items-center gap-2 mb-6 text-xs text-slate-400">
            <StepPill active={step === 1}>Account</StepPill>
            <StepPill active={step === 2}>Environment</StepPill>
            <StepPill active={step === 3}>Identity</StepPill>
            <StepPill active={step === 4}>Cloud</StepPill>
            <StepPill active={step === 5}>Payment</StepPill>
          </div>

          {step === 1 && <StepAccount onNext={next} onSignupSuccess={() => router.push('/dashboard')} />}
          {step === 2 && <StepEnvironment onNext={next} onBack={back} />}
          {step === 3 && <StepIdentity onNext={next} onBack={back} />}
          {step === 4 && <StepCloud onNext={next} onBack={back} />}
          {step === 5 && <StepPayment onBack={back} />}
        </div>
      </div>
    </main>
  );
}

function StepPill({
  active,
  children,
}: {
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`px-3 py-1 rounded-full border ${
        active
          ? "border-cyan-400 bg-cyan-400/10 text-cyan-300"
          : "border-slate-700 bg-slate-800/60"
      }`}
    >
      {children}
    </span>
  );
}

// Helper function to determine tier from employee count
function determineTierFromEmployeeCount(employeeCount: number | null): string | null {
  if (!employeeCount) return null;
  if (employeeCount <= 5) return 'free';
  if (employeeCount <= 100) return 'starter';
  if (employeeCount <= 1000) return 'professional';
  return 'enterprise';
}

// Helper function to get pricing info
function getPricingInfo(tier: string | null) {
  if (!tier) return null;
  
  const pricing = {
    free: {
      name: 'Free',
      price: 'Free',
      maxUsers: 5,
      features: ['Basic SIEM', 'Core SOAR playbooks', 'IAM hygiene checks', 'Posture scans', 'Community support']
    },
    starter: {
      name: 'Starter',
      price: '$500/month',
      maxUsers: 100,
      features: ['Full SIEM capabilities', 'SOAR playbooks', 'IAM hygiene monitoring', 'Posture scans', 'Email support', '90 days log retention']
    },
    professional: {
      name: 'Professional',
      price: '$2,000/month',
      maxUsers: 1000,
      features: ['Everything in Starter', 'Priority support', 'Custom playbooks', 'Extended log retention (180 days)', 'Advanced analytics', 'Dedicated realm (if >500 users)']
    },
    enterprise: {
      name: 'Enterprise',
      price: 'Custom pricing',
      maxUsers: 'Unlimited',
      features: ['Everything in Professional', 'Dedicated infrastructure', 'Custom SLAs', 'On-prem deployment options', '24/7 dedicated support', 'Unlimited users and organizations']
    }
  };
  
  return pricing[tier as keyof typeof pricing] || null;
}

function StepAccount({ 
  onNext, 
  onSignupSuccess 
}: { 
  onNext: () => void;
  onSignupSuccess: () => void;
}) {
  const [email, setEmail] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [employeeCount, setEmployeeCount] = useState<number | null>(null);
  const [complianceRequired, setComplianceRequired] = useState(false);
  const [serviceModel, setServiceModel] = useState<'managed' | 'byo_soc'>('managed');
  const [ticketingChoice, setTicketingChoice] = useState<'sentinelgrid' | 'jira' | 'servicenow'>('sentinelgrid');
  const [cloudAccounts, setCloudAccounts] = useState<'1-2' | '3-5' | '6-10' | '10+'>('3-5');
  const [enableAppSec, setEnableAppSec] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Determine tier from employee count
  const pricingTier = useMemo(() => determineTierFromEmployeeCount(employeeCount), [employeeCount]);
  const pricingInfo = useMemo(() => getPricingInfo(pricingTier), [pricingTier]);

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

      // Call signup API
        const response = await signupAPI({
          company_name: companyName,
          email: email,
          password: password,
          first_name: firstName,
          last_name: lastName,
          employee_count: employeeCount,
          compliance_required: complianceRequired,
          // pricing_tier will be auto-determined from employee_count on backend
        });

        if (response.success) {
          // Store tenant_id for later use
          localStorage.setItem('tenant_id', response.tenant_id);
          
          // Store email and password temporarily for payment success page auto-login
          localStorage.setItem('signup_email', email);
          localStorage.setItem('signup_password', password);
          
          // Store signup data for payment step
          localStorage.setItem('signup_pricing_tier', pricingTier || 'starter');
          localStorage.setItem('signup_employee_count', employeeCount.toString());
          localStorage.setItem('signup_compliance_required', complianceRequired.toString());
          localStorage.setItem('signup_service_model', serviceModel);
          localStorage.setItem('signup_ticketing', ticketingChoice);
          localStorage.setItem('signup_cloud_accounts', cloudAccounts);
          localStorage.setItem('signup_enable_appsec', enableAppSec.toString());
          
          // Always proceed to next step in wizard after successful signup
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
          <label htmlFor="email" className="block text-xs text-slate-300 mb-1">
            Work email
          </label>
          <input
            id="email"
            required
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
            placeholder="you@company.com"
            autoComplete="email"
          />
        </div>
        <div>
          <label htmlFor="company" className="block text-xs text-slate-300 mb-1">
            Company name
          </label>
          <input
            id="company"
            required
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
            placeholder="Company Inc."
          />
        </div>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label htmlFor="name" className="block text-xs text-slate-300 mb-1">
            Your name
          </label>
          <input
            id="name"
            required
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
            placeholder="Jane Doe"
            autoComplete="name"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-xs text-slate-300 mb-1">
            Password
          </label>
          <input
            id="password"
            required
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
            placeholder="••••••••"
            autoComplete="new-password"
            minLength={8}
          />
          <p className="text-xs text-slate-400 mt-1">
            Must be at least 8 characters with uppercase, lowercase, and number
          </p>
        </div>
      </div>
      
      {/* Company Details Section */}
      <div className="pt-4 border-t border-slate-800">
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Company Details</h3>
        
        <div className="mb-4">
          <label htmlFor="employeeCount" className="block text-xs text-slate-300 mb-1">
            Company size (number of employees) <span className="text-red-400">*</span>
          </label>
          <select
            id="employeeCount"
            required
            value={employeeCount || ''}
            onChange={(e) => setEmployeeCount(e.target.value ? parseInt(e.target.value) : null)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
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
        
        {/* Pricing Display */}
        {pricingInfo && (
          <div className="mb-4 rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-cyan-300">{pricingInfo.name} Plan</h4>
              <span className="text-lg font-bold text-cyan-400">{pricingInfo.price}</span>
            </div>
            <p className="text-xs text-slate-400 mb-2">
              Up to {pricingInfo.maxUsers} {typeof pricingInfo.maxUsers === 'number' ? 'users' : 'users'}
            </p>
            <ul className="text-xs text-slate-300 space-y-1">
              {pricingInfo.features.slice(0, 3).map((feature, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="text-cyan-400 mr-2">•</span>
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
            {complianceRequired && pricingTier !== 'enterprise' && (
              <div className="mt-2 pt-2 border-t border-cyan-500/20">
                <p className="text-xs text-amber-300">
                  ⚠️ Compliance requirement will upgrade you to a dedicated infrastructure plan
                </p>
              </div>
            )}
          </div>
        )}
        
        <div className="mb-4">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={complianceRequired}
              onChange={(e) => setComplianceRequired(e.target.checked)}
              className="mt-1 rounded border-slate-600"
            />
            <span className="text-xs text-slate-300">
              We require dedicated infrastructure for compliance (HIPAA, SOC 2, GDPR, etc.)
            </span>
          </label>
        </div>

        <div className="grid md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <p className="text-xs text-slate-300 font-semibold">Who runs the SOC?</p>
            <div className="flex flex-col gap-2 text-xs text-slate-300">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="serviceModel"
                  value="managed"
                  checked={serviceModel === 'managed'}
                  onChange={() => setServiceModel('managed')}
                  className="rounded border-slate-600"
                />
                <span>SentinelGrid manages SOC (recommended)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="serviceModel"
                  value="byo_soc"
                  checked={serviceModel === 'byo_soc'}
                  onChange={() => setServiceModel('byo_soc')}
                  className="rounded border-slate-600"
                />
                <span>Use my SOC; SentinelGrid runs SIEM/SOAR</span>
              </label>
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-xs text-slate-300 font-semibold">Ticketing</p>
            <select
              value={ticketingChoice}
              onChange={(e) => setTicketingChoice(e.target.value as typeof ticketingChoice)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 disabled:opacity-50"
              disabled={serviceModel === 'managed' && ticketingChoice === 'sentinelgrid'}
            >
              <option value="sentinelgrid">Use SentinelGrid ticketing (default)</option>
              <option value="jira">Jira</option>
              <option value="servicenow">ServiceNow</option>
            </select>
            <p className="text-xs text-slate-400">
              If you pick Jira/ServiceNow, we&apos;ll ask for connection details after signup.
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-3 mt-4">
          <div>
            <label htmlFor="cloudAccounts" className="block text-xs text-slate-300 mb-1">
              Cloud accounts (estimate)
            </label>
            <select
              id="cloudAccounts"
              value={cloudAccounts}
              onChange={(e) => setCloudAccounts(e.target.value as typeof cloudAccounts)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
            >
              <option value="1-2">1-2</option>
              <option value="3-5">3-5</option>
              <option value="6-10">6-10</option>
              <option value="10+">10+</option>
            </select>
          </div>
          <div className="flex items-center gap-3 bg-slate-900/40 border border-slate-800 rounded-lg px-3 py-2">
            <input
              type="checkbox"
              checked={enableAppSec}
              onChange={(e) => setEnableAppSec(e.target.checked)}
              className="rounded border-slate-600"
            />
            <div className="text-xs text-slate-300">
              <p className="font-semibold">Enable App Security & Git scans</p>
              <p className="text-slate-400">We&apos;ll collect repo details after signup.</p>
            </div>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 pt-2">
        <input type="checkbox" id="terms" required className="rounded" />
        <label htmlFor="terms" className="text-xs text-slate-400">
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
        className="mt-4 inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Creating account...' : 'Continue'}
      </button>
    </form>
  );
}

function StepEnvironment({
  onNext,
  onBack,
}: {
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        onNext();
      }}
    >
      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-300 mb-1">Primary environment</label>
          <select className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200">
            <option>Cloud (AWS / GCP / Azure)</option>
            <option>SaaS‑only (Google Workspace / M365)</option>
            <option>On‑prem / hybrid</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-300 mb-1">Cloud accounts</label>
          <select className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200">
            <option>1-2 accounts</option>
            <option>3-5 accounts</option>
            <option>6-10 accounts</option>
            <option>10+ accounts</option>
          </select>
        </div>
      </div>
      <div>
        <label className="block text-xs text-slate-300 mb-1">Identity provider</label>
        <select className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200">
          <option>Use SentinelGrid Identity (recommended for small teams)</option>
          <option>Google Workspace</option>
          <option>Microsoft 365 / Entra ID</option>
          <option>Okta</option>
          <option>Keycloak / Other</option>
        </select>
        <p className="text-xs text-slate-400 mt-1">
          We&apos;ll act as your secure identity provider, with MFA and SSO built‑in. Or connect
          your existing SSO.
        </p>
      </div>
      <div className="flex justify-between pt-2">
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-slate-300 hover:text-slate-100"
        >
          ← Back
        </button>
        <button
          type="submit"
          className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
        >
          Continue
        </button>
      </div>
    </form>
  );
}

function StepIdentity({
  onNext,
  onBack,
}: {
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-300">
        Connect your identity provider so we can understand your users, admins, and sign‑ins.
      </p>
      <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-4">
        <h3 className="text-sm font-semibold mb-1">Connect identity</h3>
        <p className="text-xs text-slate-300 mb-3">
          Google Workspace, Microsoft 365 / Entra, Okta or Keycloak. Or use SentinelGrid
          Identity — we&apos;ll act as your IdP with MFA and SSO built‑in.
        </p>
        <button
          type="button"
          onClick={onNext}
          className="w-full rounded-full border border-slate-600 text-xs py-2 hover:border-cyan-400 transition-colors"
        >
          Open identity setup
        </button>
      </div>
      <div className="flex justify-between pt-2">
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-slate-300 hover:text-slate-100"
        >
          ← Back
        </button>
        <button
          type="button"
          onClick={onNext}
          className="text-xs text-slate-300 hover:text-slate-100"
        >
          Skip for now →
        </button>
      </div>
    </div>
  );
}

function StepCloud({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-300">
        Connect your cloud so we can ingest audit logs and security findings from your cloud
        accounts.
      </p>
      <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-4">
        <h3 className="text-sm font-semibold mb-1">Connect cloud</h3>
        <p className="text-xs text-slate-300 mb-3">
          Start with AWS: we&apos;ll give you a CloudFormation link for safe, read‑only access.
          We&apos;ll set up CloudTrail and GuardDuty export.
        </p>
        <button className="w-full rounded-full border border-slate-600 text-xs py-2 hover:border-cyan-400 transition-colors">
          Open cloud setup
        </button>
      </div>
      <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
        <p className="text-xs text-green-300">
          ✅ Once connected, you&apos;ll see your first security insights within a few hours.
        </p>
      </div>
      <div className="flex justify-between pt-2">
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-slate-300 hover:text-slate-100"
        >
          ← Back
        </button>
        <button
          type="button"
          onClick={onNext}
          className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
        >
          Continue to Payment
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
    tenantId: string;
    pricingTier: string;
    employeeCount: number;
    cloudAccounts: number;
    complianceRequired: boolean;
    serviceModel: 'managed' | 'byo_soc';
    ticketing: 'sentinelgrid' | 'jira' | 'servicenow';
    enableAppSec: boolean;
  } | null>(null);

  useEffect(() => {
    const tenantId = localStorage.getItem('tenant_id');
    const pricingTier = localStorage.getItem('signup_pricing_tier') || 'starter';
    const employeeCount = parseInt(localStorage.getItem('signup_employee_count') || '26', 10);
    const complianceRequired = localStorage.getItem('signup_compliance_required') === 'true';
    const storedServiceModel = (localStorage.getItem('signup_service_model') as 'managed' | 'byo_soc') || 'managed';
    const storedTicketing = (localStorage.getItem('signup_ticketing') as 'sentinelgrid' | 'jira' | 'servicenow') || 'sentinelgrid';
    const storedCloudAccounts = localStorage.getItem('signup_cloud_accounts') || '3-5';
    const storedEnableAppSec = localStorage.getItem('signup_enable_appsec') !== 'false';
    
    if (!tenantId) {
      setError('Missing signup data. Please start over.');
      return;
    }
    const cloudAccounts = (() => {
      switch (storedCloudAccounts) {
        case '1-2':
          return 2;
        case '3-5':
          return 5;
        case '6-10':
          return 10;
        case '10+':
          return 12;
        default:
          return 5;
      }
    })();
    setSignupData({
      tenantId,
      pricingTier,
      employeeCount,
      cloudAccounts,
      complianceRequired,
      serviceModel: storedServiceModel,
      ticketing: storedTicketing,
      enableAppSec: storedEnableAppSec,
    });
    calculatePricing(tenantId, pricingTier, employeeCount, cloudAccounts, complianceRequired, billingPeriod, storedServiceModel);
  }, []); // initial load
    // eslint-disable-next-line react-hooks/exhaustive-deps

  const calculatePricing = async (
    tenantId: string, tier: string, employees: number,
    cloudAccounts: number, compliance: boolean, period: 'monthly' | 'yearly',
    serviceModel?: 'managed' | 'byo_soc'
  ) => {
    try {
      setLoading(true);
      const pricingInfo = await calculatePrice({
        pricing_tier: tier, employee_count: employees,
        billing_period: period, cloud_accounts: cloudAccounts,
        compliance_required: compliance, service_model: serviceModel
      });
      setPricing(pricingInfo);
    } catch (err: any) {
      setError(err.message || 'Failed to calculate pricing');
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (signupData && billingPeriod) {
      calculatePricing(signupData.tenantId, signupData.pricingTier,
        signupData.employeeCount, signupData.cloudAccounts,
        signupData.complianceRequired, billingPeriod, signupData.serviceModel);
    }
    // We intentionally avoid adding calculatePrice to deps; it's stable in this scope.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [billingPeriod, signupData]);

  const handlePayment = async () => {
    if (!signupData || !pricing) return;
    if (pricing.requires_sales_contact || pricing.total === null) {
      window.location.href = '/contact?tier=enterprise';
      return;
    }
    if (pricing.total === 0) {
      router.push('/dashboard');
      return;
    }
    try {
      setProcessingPayment(true);
      setError(null);
      const successUrl = `${window.location.origin}/signup/payment-success?session_id={CHECKOUT_SESSION_ID}&tenant_id=${signupData.tenantId}`;
      const cancelUrl = `${window.location.origin}/signup?step=5`;
      const checkout = await createCheckoutSession({
        tenant_id: signupData.tenantId, pricing_tier: signupData.pricingTier,
        employee_count: signupData.employeeCount, billing_period: billingPeriod,
        cloud_accounts: signupData.cloudAccounts, compliance_required: signupData.complianceRequired,
        service_model: signupData.serviceModel, ticketing: signupData.ticketing,
        enable_appsec: signupData.enableAppSec,
        success_url: successUrl, cancel_url: cancelUrl
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
    return <div className="space-y-4"><p className="text-sm text-slate-300">Loading payment information...</p></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Complete your subscription</h2>
        <p className="text-sm text-slate-300">Choose your billing period and complete payment to activate your SentinelGrid account.</p>
        <p className="text-xs text-slate-400 mt-2">
          Selections: {signupData.serviceModel === 'managed' ? 'Managed SOC' : 'BYO SOC'} · Ticketing: {signupData.ticketing} · Cloud accounts: {signupData.cloudAccounts} · AppSec/Git scans: {signupData.enableAppSec ? 'On' : 'Off'}
        </p>
      </div>
      <div className="flex items-center gap-4 p-4 bg-slate-800/60 rounded-lg border border-slate-700">
        <button type="button" onClick={() => setBillingPeriod('monthly')}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
            billingPeriod === 'monthly' ? 'bg-cyan-400 text-slate-950' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}>Monthly</button>
        <button type="button" onClick={() => setBillingPeriod('yearly')}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors relative ${
            billingPeriod === 'yearly' ? 'bg-cyan-400 text-slate-950' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}>
          Yearly<span className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-0.5 rounded-full">Save 17%</span>
        </button>
      </div>
      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">Calculating pricing...</p>
        </div>
      ) : pricing ? (
        <div className="space-y-4">
          <div className="bg-slate-800/60 rounded-lg border border-slate-700 p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-slate-300">Base Plan</span>
              <span className="text-lg font-semibold text-cyan-400">
                {pricing.base_price !== null ? `$${(pricing.base_price / 100).toFixed(2)}` : 'Custom'}/{billingPeriod === 'monthly' ? 'mo' : 'yr'}
              </span>
            </div>
            <p className="text-xs text-slate-400">{signupData.pricingTier.charAt(0).toUpperCase() + signupData.pricingTier.slice(1)} Tier</p>
          </div>
          {pricing.addons.length > 0 && (
            <div className="bg-slate-800/60 rounded-lg border border-slate-700 p-4">
              <h3 className="text-sm font-semibold text-slate-200 mb-3">Add-ons</h3>
              <div className="space-y-2">
                {pricing.addons.map((addon, idx) => (
                  <div key={idx} className="flex justify-between items-center">
                    <span className="text-sm text-slate-300">{addon.name}</span>
                    <span className="text-sm font-medium text-cyan-400">{addon.display}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="bg-gradient-to-r from-cyan-500/20 to-cyan-400/20 rounded-lg border border-cyan-400/30 p-4">
            <div className="flex justify-between items-center">
              <span className="text-lg font-semibold text-slate-200">Total</span>
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
        <button type="button" onClick={onBack} className="text-xs text-slate-300 hover:text-slate-100">← Back</button>
        <button type="button" onClick={handlePayment} disabled={loading || processingPayment || !pricing}
          className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-semibold bg-gradient-to-r from-cyan-400 to-cyan-500 text-slate-950 hover:brightness-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20">
          {processingPayment ? (
            <> <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-slate-950 mr-2"></div> Processing... </>
          ) : pricing?.requires_sales_contact ? 'Contact Sales' : pricing?.total === 0 ? 'Complete Setup (Free)' : `Pay ${pricing?.display || ''}`}
        </button>
      </div>
      <div className="flex items-center justify-center gap-2 text-xs text-slate-400 pt-4 border-t border-slate-800">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <span>Secure payment powered by Stripe</span>
      </div>
    </div>
  );
}
