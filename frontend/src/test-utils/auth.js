// Test helpers to seed auth/tenant context and quiet auth logs
const originalConsoleLog = console.log;

function seedTestAuth() {
  if (typeof window === 'undefined' || !globalThis.localStorage) return;
  try {
    localStorage.setItem('tenant_id', 'test-tenant');
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('user', JSON.stringify({ id: 'user-1', email: 'test@example.com' }));
  } catch {
    // ignore if storage is unavailable in environment
  }
}

function silenceAuthLogs() {
  console.log = (...args) => {
    const msg = args.find((a) => typeof a === 'string');
    if (msg && msg.includes('AuthProvider')) return;
    return originalConsoleLog(...args);
  };
}

module.exports = {
  seedTestAuth,
  silenceAuthLogs,
};
