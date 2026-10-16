export function resetTestStorage() {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.clear();
  window.sessionStorage.clear();

  document.cookie.split(';').forEach((cookie) => {
    const [name] = cookie.split('=');
    if (name && name.trim()) {
      document.cookie = `${name.trim()}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`;
    }
  });
}
