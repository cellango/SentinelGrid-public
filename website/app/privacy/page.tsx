/* eslint react/no-unescaped-entities: 0 */
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import Link from "next/link";

export default function PrivacyPage() {
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
          <h1 className="text-4xl font-semibold mb-4">Privacy Policy</h1>
          <p className="text-slate-400 text-sm">
            Last updated: {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>

        <div className="prose prose-invert max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
            <p className="text-slate-300 leading-relaxed">
              SentinelGrid ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy
              explains how we collect, use, disclose, and safeguard your information when you use our
              Cybersecurity-as-a-Service platform ("Service").
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Information We Collect</h2>
            
            <h3 className="text-xl font-semibold mb-3 mt-6">2.1 Account Information</h3>
            <p className="text-slate-300 leading-relaxed mb-4">
              When you create an account, we collect:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Name and email address</li>
              <li>Company name and information</li>
              <li>Billing information (processed securely through payment processors)</li>
              <li>Authentication credentials (stored using industry-standard encryption)</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">2.2 Security Telemetry Data</h3>
            <p className="text-slate-300 leading-relaxed mb-4">
              To provide security services, we collect and process:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Identity provider logs (sign-in events, directory information)</li>
              <li>Cloud infrastructure logs (CloudTrail, GuardDuty, Config, etc.)</li>
              <li>Endpoint security logs (when agents are installed)</li>
              <li>Email metadata (for phishing detection)</li>
              <li>Security alerts and incident data</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">2.3 Usage Information</h3>
            <p className="text-slate-300 leading-relaxed mb-4">
              We collect information about how you use the Service:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Feature usage and interactions</li>
              <li>API calls and requests</li>
              <li>Configuration changes</li>
              <li>Support interactions</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3 mt-6">2.4 Technical Information</h3>
            <p className="text-slate-300 leading-relaxed mb-4">
              We automatically collect certain technical information:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>IP addresses and network information</li>
              <li>Browser type and version</li>
              <li>Device information</li>
              <li>Log files and error reports</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. How We Use Your Information</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              We use the information we collect to:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Provide, maintain, and improve the Service</li>
              <li>Detect, prevent, and respond to security threats</li>
              <li>Analyze security events and generate alerts</li>
              <li>Provide AI-driven security analysis and recommendations</li>
              <li>Process payments and manage subscriptions</li>
              <li>Send service-related communications</li>
              <li>Respond to your inquiries and provide support</li>
              <li>Comply with legal obligations</li>
              <li>Protect our rights and prevent fraud</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Data Security and Encryption</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              We implement industry-standard security measures to protect your data:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>
                <strong>Encryption in Transit:</strong> All data transmitted to and from the Service is encrypted
                using TLS 1.2 or higher
              </li>
              <li>
                <strong>Encryption at Rest:</strong> All stored data is encrypted using industry-standard encryption
                algorithms
              </li>
              <li>
                <strong>Tenant Isolation:</strong> Each customer&apos;s data is stored in isolated, tenant-specific
                indexes and storage paths
              </li>
              <li>
                <strong>Access Controls:</strong> We implement least-privilege access controls and multi-factor
                authentication for our systems
              </li>
              <li>
                <strong>Regular Audits:</strong> We conduct regular security audits and assessments
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Data Retention</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              We retain your data for the following periods:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>
                <strong>Active Subscriptions:</strong> Data is retained for the duration of your subscription
              </li>
              <li>
                <strong>Hot Storage:</strong> Recent security logs and alerts are kept in hot storage for 30 days
                (configurable)
              </li>
              <li>
                <strong>Archive Storage:</strong> Historical data is archived for up to 12 months (configurable)
              </li>
              <li>
                <strong>After Termination:</strong> Data is retained for 30 days after account termination, then
                permanently deleted
              </li>
              <li>
                <strong>Legal Requirements:</strong> We may retain certain data longer if required by law or legal
                proceedings
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Data Sharing and Disclosure</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              We do not sell, rent, or trade your data. We may share your information only in the following
              circumstances:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>
                <strong>Service Providers:</strong> With trusted third-party service providers who assist in
                operating our Service (e.g., cloud infrastructure, payment processors), subject to strict
                confidentiality agreements
              </li>
              <li>
                <strong>Legal Requirements:</strong> When required by law, court order, or government regulation
              </li>
              <li>
                <strong>Protection of Rights:</strong> To protect our rights, property, or safety, or that of our
                users
              </li>
              <li>
                <strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets
                (with notice to affected users)
              </li>
              <li>
                <strong>With Your Consent:</strong> When you explicitly authorize us to share your information
              </li>
            </ul>
            <p className="text-slate-300 leading-relaxed mt-4">
              <strong>Important:</strong> We never share your security telemetry data or customer-specific
              information with other customers or for marketing purposes.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. AI and Machine Learning</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              Our Service uses AI and machine learning models to analyze security data. Important points:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>
                <strong>Local Processing:</strong> AI models run in our controlled environment, not on public
                third-party services
              </li>
              <li>
                <strong>No Cross-Tenant Training:</strong> Your data is never used to train models shared with
                other customers
              </li>
              <li>
                <strong>Per-Tenant Adapters:</strong> We use tenant-specific model adapters to ensure your
                incidents don&apos;t influence other customers&apos; results
              </li>
              <li>
                <strong>No Public AI Services:</strong> We do not send your security logs or incidents to public
                AI services (e.g., OpenAI, Anthropic) without your explicit consent
              </li>
              <li>
                <strong>Opt-Out:</strong> You can disable certain AI features per tenant if required
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Your Rights and Choices</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              You have the following rights regarding your data:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>
                <strong>Access:</strong> Request access to your personal data and security logs
              </li>
              <li>
                <strong>Correction:</strong> Update or correct inaccurate information in your account
              </li>
              <li>
                <strong>Deletion:</strong> Request deletion of your data (subject to legal retention requirements)
              </li>
              <li>
                <strong>Export:</strong> Export your data in standard formats (CSV, JSON, etc.)
              </li>
              <li>
                <strong>Opt-Out:</strong> Opt out of certain data processing activities where applicable
              </li>
              <li>
                <strong>Account Closure:</strong> Close your account and request data deletion
              </li>
            </ul>
            <p className="text-slate-300 leading-relaxed mt-4">
              To exercise these rights, contact us at privacy@sentinelgrid.com.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. International Data Transfers</h2>
            <p className="text-slate-300 leading-relaxed">
              Your data is stored in the region you select during setup. If you choose a specific region, we
              will store your data in that region. We may transfer data to other regions only with your explicit
              consent or as necessary to provide the Service, and we ensure appropriate safeguards are in place.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Children&apos;s Privacy</h2>
            <p className="text-slate-300 leading-relaxed">
              Our Service is not intended for individuals under the age of 18. We do not knowingly collect
              personal information from children. If you believe we have collected information from a child,
              please contact us immediately.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Cookies and Tracking</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              We use cookies and similar technologies to:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>Maintain your session and authentication state</li>
              <li>Remember your preferences and settings</li>
              <li>Analyze Service usage and performance</li>
              <li>Provide security features</li>
            </ul>
            <p className="text-slate-300 leading-relaxed mt-4">
              You can control cookies through your browser settings, but disabling cookies may affect Service
              functionality.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. Changes to This Privacy Policy</h2>
            <p className="text-slate-300 leading-relaxed">
              We may update this Privacy Policy from time to time. We will notify you of material changes via
              email or through the Service. The "Last updated" date at the top of this page indicates when the
              policy was last revised.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">13. Compliance</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              We are committed to complying with applicable data protection laws, including:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>GDPR (General Data Protection Regulation) for EU users</li>
              <li>CCPA (California Consumer Privacy Act) for California residents</li>
              <li>Other applicable regional data protection laws</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">14. Contact Us</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              If you have questions, concerns, or requests regarding this Privacy Policy or our data practices,
              please contact us:
            </p>
            <p className="text-slate-300 leading-relaxed">
              <strong>Privacy Officer</strong><br />
              Email: privacy@sentinelgrid.com<br />
              Address: [Your Company Address]
            </p>
            <p className="text-slate-300 leading-relaxed mt-4">
              For data protection inquiries in the EU, contact our Data Protection Officer at:
              dpo@sentinelgrid.com
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </main>
  );
}
