/* eslint react/no-unescaped-entities: 0 */
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <div className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-8">
          <Link
            href="/"
            className="text-sm text-slate-400 hover:text-slate-200 mb-4 inline-block"
          >
            ← Back to home
          </Link>
          <h1 className="text-4xl font-semibold mb-4">Terms of Service</h1>
          <p className="text-slate-400 text-sm">
            Last updated: {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>

        <div className="prose prose-invert max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Agreement to Terms</h2>
            <p className="text-slate-300 leading-relaxed">
              By accessing or using SentinelGrid ("Service"), you agree to be bound by these Terms of Service
              ("Terms"). If you disagree with any part of these terms, you may not access the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Description of Service</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              SentinelGrid is a Cybersecurity-as-a-Service platform that provides:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Managed SIEM + SOAR (Security Information and Event Management and Orchestration)</li>
              <li>AI-driven security operations center (SOC) services</li>
              <li>Identity and Access Management (IAM) hygiene monitoring</li>
              <li>Cloud security posture management</li>
              <li>Automated threat detection and response</li>
              <li>Identity provider (IdP) services and SSO capabilities</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. Account Registration</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              To use the Service, you must:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Provide accurate, current, and complete information during registration</li>
              <li>Maintain and update your account information to keep it accurate</li>
              <li>Maintain the security of your account credentials</li>
              <li>Accept responsibility for all activities that occur under your account</li>
              <li>Notify us immediately of any unauthorized use of your account</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Acceptable Use</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              You agree not to:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Use the Service for any illegal purpose or in violation of any laws</li>
              <li>Transmit any malicious code, viruses, or harmful data</li>
              <li>Attempt to gain unauthorized access to the Service or related systems</li>
              <li>Interfere with or disrupt the Service or servers connected to the Service</li>
              <li>Use the Service to monitor or attack third-party systems without authorization</li>
              <li>Reverse engineer, decompile, or disassemble any part of the Service</li>
              <li>Use automated systems to access the Service without permission</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Data and Privacy</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              Your use of the Service is also governed by our{" "}
              <Link href="/privacy" className="text-cyan-400 hover:underline">
                Privacy Policy
              </Link>
              . Key points:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>We process security logs and telemetry data to provide security services</li>
              <li>Data is encrypted in transit and at rest</li>
              <li>Data is isolated per tenant and not shared between customers</li>
              <li>We do not use your data to train public AI models</li>
              <li>You retain ownership of your data</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Service Availability</h2>
            <p className="text-slate-300 leading-relaxed">
              We strive to maintain high availability but do not guarantee uninterrupted access to the Service.
              We may perform maintenance, updates, or modifications that may temporarily interrupt service.
              We will provide reasonable notice of planned maintenance when possible.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Billing and Payment</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              Subscription fees are billed in advance on a monthly or annual basis. You agree to pay all fees
              associated with your subscription. Fees are non-refundable except as required by law or as
              explicitly stated in your subscription agreement.
            </p>
            <p className="text-slate-300 leading-relaxed">
              We reserve the right to change our pricing with 30 days notice. Price changes will not affect
              your current billing cycle but will apply to subsequent renewals.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Intellectual Property</h2>
            <p className="text-slate-300 leading-relaxed">
              The Service, including all software, designs, text, graphics, and other content, is owned by
              SentinelGrid or its licensors and is protected by copyright, trademark, and other intellectual
              property laws. You may not copy, modify, distribute, or create derivative works without our
              express written permission.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Limitation of Liability</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, SENTINELGRID SHALL NOT BE LIABLE FOR ANY INDIRECT,
              INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF
              PROFITS, DATA, OR BUSINESS INTERRUPTION.
            </p>
            <p className="text-slate-300 leading-relaxed">
              Our total liability for any claims arising from or related to the Service shall not exceed the
              amount you paid to us in the 12 months preceding the claim.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Indemnification</h2>
            <p className="text-slate-300 leading-relaxed">
              You agree to indemnify and hold harmless SentinelGrid, its officers, directors, employees, and
              agents from any claims, damages, losses, liabilities, and expenses (including legal fees) arising
              from your use of the Service, violation of these Terms, or infringement of any rights of another.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Termination</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              Either party may terminate this agreement at any time. Upon termination:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Your right to access and use the Service will immediately cease</li>
              <li>You remain responsible for all fees incurred prior to termination</li>
              <li>We will retain your data for 30 days after termination, after which it will be deleted</li>
              <li>You may export your data prior to termination</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. Changes to Terms</h2>
            <p className="text-slate-300 leading-relaxed">
              We reserve the right to modify these Terms at any time. We will notify you of material changes
              via email or through the Service. Your continued use of the Service after such modifications
              constitutes acceptance of the updated Terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">13. Governing Law</h2>
            <p className="text-slate-300 leading-relaxed">
              These Terms shall be governed by and construed in accordance with the laws of [Your Jurisdiction],
              without regard to its conflict of law provisions. Any disputes arising from these Terms or the
              Service shall be resolved in the courts of [Your Jurisdiction].
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">14. Contact Information</h2>
            <p className="text-slate-300 leading-relaxed">
              If you have any questions about these Terms, please contact us at:
            </p>
            <p className="text-slate-300 leading-relaxed mt-2">
              Email: legal@sentinelgrid.com<br />
              Address: [Your Company Address]
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </main>
  );
}
