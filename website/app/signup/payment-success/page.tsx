"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { handlePaymentSuccess } from "@/lib/api/payment";
import { login as loginAPI } from "@/lib/api/auth";
import { Header } from "@/components/Header";

function PaymentSuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const processPayment = async () => {
      const sessionId = searchParams.get('session_id');
      const tenantId = searchParams.get('tenant_id');

      if (!sessionId || !tenantId) {
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
        
        // Confirm payment with backend
        const result = await handlePaymentSuccess(sessionId, tenantId);

        // Get email and password from localStorage (stored during signup)
        const email = localStorage.getItem('signup_email');
        const password = localStorage.getItem('signup_password');

        if (email && password) {
          // Auto-login the user
          try {
            await loginAPI(email, password, false);
            console.log('Auto-login successful');
          } catch (loginErr: any) {
            console.error('Auto-login failed:', loginErr);
            // Continue anyway - user can log in manually
          }
          
          // Clear temporary signup data
          localStorage.removeItem('signup_email');
          localStorage.removeItem('signup_password');
        } else {
          console.warn('Email/password not found in localStorage - user will need to log in manually');
        }

        setStatus('success');
        
        // Redirect to dashboard after a brief delay
        setTimeout(() => {
          router.push('/dashboard');
        }, 2000);
      } catch (err: any) {
        console.error('Payment processing error:', err);
        setError(err.message || 'Failed to process payment');
        setStatus('error');
      }
    };

    processPayment();
  }, [searchParams, router]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <div className="flex items-center justify-center min-h-[80vh] px-4">
        <div className="max-w-md w-full bg-slate-900/70 border border-slate-800 rounded-2xl p-8 text-center">
          {status === 'processing' && (
            <>
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-cyan-400 mx-auto mb-6"></div>
              <h1 className="text-2xl font-semibold mb-2">Processing your payment...</h1>
              <p className="text-slate-300">Please wait while we confirm your subscription.</p>
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
              <p className="text-slate-300 mb-6">Your subscription is now active. Redirecting to your dashboard...</p>
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-cyan-400 mx-auto"></div>
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
              <p className="text-slate-300 mb-6">{error || 'An error occurred while processing your payment.'}</p>
              <button
                onClick={() => router.push('/signup?step=5')}
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
      <main className="min-h-screen bg-slate-950 text-slate-50">
        <Header />
        <div className="flex items-center justify-center min-h-[80vh] px-4">
          <div className="max-w-md w-full bg-slate-900/70 border border-slate-800 rounded-2xl p-8 text-center">
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

