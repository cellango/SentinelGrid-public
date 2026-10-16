"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { handlePaymentSuccess } from "@/lib/api/payment";
import { Header } from "@/components/Header";
import { recordPaymentSucceeded } from "@/lib/onboarding/metrics";

function PaymentSuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState<string | null>(null);
  const [loginUrl, setLoginUrl] = useState<string>("/login");

  useEffect(() => {
    const processPayment = async () => {
      const sessionId = searchParams.get('session_id');
      const leadId = searchParams.get('lead_id');

      if (!sessionId || !leadId) {
        setError('Missing payment information');
        setStatus('error');
        return;
      }

      try {
        // Check if this is dev mode (session_id starts with "dev_session_")
        const isDevMode = sessionId.startsWith('dev_session_');
        
        if (isDevMode) {
          console.log('DEV MODE: Processing payment without Stripe verification');
        }
        
        // Get session token for account provisioning
        const provisioningToken = sessionStorage.getItem('signup_session_token') || undefined;
        if (!provisioningToken) {
          throw new Error('Missing signup provisioning token');
        }
        console.log('💳 Payment success - sessionId:', sessionId, 'leadId:', leadId);
        
        // Confirm payment with backend (creates account from lead)
        console.log('⏳ Calling handlePaymentSuccess...');
        const result = await handlePaymentSuccess(sessionId, leadId, provisioningToken);
        console.log('✅ Payment success response:', {
          success: result.success,
          password_reset_required: result.password_reset_required,
          user_verified: result.user_verified,
          email: result.email
        });

        if (!result.success) {
          throw new Error(result.message || 'Payment processing failed');
        }

        // Store tenant_id for later use
        if (result.tenant_id) {
          localStorage.setItem('tenant_id', result.tenant_id);
        }
        recordPaymentSucceeded({
          tenantId: result.tenant_id,
          planTier: localStorage.getItem('signup_plan_tier') || undefined,
        });

        // Get email from result or localStorage
        const email = result.email || localStorage.getItem('signup_email');
        if (email) {
          setLoginUrl(`/login?message=account_created&email=${encodeURIComponent(email)}`);
        }

        // Clear temporary signup data
        localStorage.removeItem('signup_email');
        sessionStorage.removeItem('signup_session_token');
        localStorage.removeItem('lead_id');
        localStorage.removeItem('signup_user_count');
        localStorage.removeItem('signup_compliance_required');
        localStorage.removeItem('signup_pricing');

        setStatus('success');
        console.log('✅ Payment status set to success');
        
        // Wait briefly for provisioning, then guide user to login
        const waitTime = result.user_verified ? 1200 : 2500;
        console.log(`⏳ Waiting ${waitTime}ms before showing login prompt...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        router.push(loginUrl || '/login?message=account_created');
      } catch (err: any) {
        console.error('Payment processing error:', err);
        setError(err.message || 'Failed to process payment');
        setStatus('error');
      }
    };

    processPayment();
  }, [searchParams, router]);

  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <div className="flex items-center justify-center min-h-[80vh] px-4">
        <div className="max-w-md w-full bg-bg-alt/90 border border-border rounded-2xl p-8 text-center">
          {status === 'processing' && (
            <>
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-cyan-400 mx-auto mb-6"></div>
              <h1 className="text-2xl font-semibold mb-2">Processing your payment...</h1>
              <p className="text-text-muted">Please wait while we confirm your subscription.</p>
            </>
          )}
          
          {status === 'success' && (
            <>
              <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="text-2xl font-semibold mb-2">Payment Successful!</h1>
              <p className="text-text-muted mb-4">
                Your subscription is active. Please sign in with the credentials you just set to continue.
              </p>
              <button
                onClick={() => router.push(loginUrl)}
                className="w-full inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-semibold bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
                data-testid="payment-success-login-btn"
              >
                Continue to login
              </button>
              <p className="text-xs text-text-main0 mt-3">We&apos;ll redirect you automatically in a moment.</p>
            </>
          )}
          
          {status === 'error' && (
            <>
              <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h1 className="text-2xl font-semibold mb-2">Payment Error</h1>
              <p className="text-text-muted mb-6">{error || 'An error occurred while processing your payment.'}</p>
              <button
                onClick={() => router.push('/signup?step=2')}
                className="inline-flex items-center justify-center rounded-full px-6 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                Try Again
              </button>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-bg text-text-main">
        <Header />
        <div className="flex items-center justify-center min-h-[80vh] px-4">
          <div className="max-w-md w-full bg-bg-alt/90 border border-border rounded-2xl p-8 text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-cyan-400 mx-auto mb-6"></div>
            <h1 className="text-2xl font-semibold mb-2">Loading...</h1>
          </div>
        </div>
      </main>
    }>
      <PaymentSuccessContent />
    </Suspense>
  );
}
