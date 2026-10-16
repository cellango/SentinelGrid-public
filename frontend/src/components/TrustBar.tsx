export function TrustBar() {
  return (
    <div className="mt-8 pt-6 border-t border-slate-800">
      <div className="flex flex-wrap gap-6 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="text-green-400">✓</span>
          <span>Your data stays in your cloud / region</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-400">✓</span>
          <span>Logs are encrypted and tenant‑isolated</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-400">✓</span>
          <span>No customer data used to train public AI models</span>
        </div>
      </div>
    </div>
  );
}

