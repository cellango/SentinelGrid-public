/**
 * Internationalization (i18n) Module
 * Lightweight i18n system for SentinelGrid.
 *
 * Usage:
 *   import { t, useLocale } from '@/lib/i18n';
 *
 *   // Simple translation
 *   t('nav.dashboard')  // "Dashboard"
 *
 *   // With interpolation
 *   t('time.minutesAgo', { count: 5 })  // "5 minutes ago"
 *
 *   // React hook for locale context
 *   const { locale, setLocale } = useLocale();
 */

import { messages, DEFAULT_LOCALE, type Locale, type MessageKey } from './messages';

let currentLocale: Locale = DEFAULT_LOCALE;

/**
 * Get a translated message by key.
 * Falls back to English if the key is missing in the current locale.
 */
export function t(key: MessageKey, params?: Record<string, string | number>): string {
  const catalog = messages[currentLocale] || messages.en;
  let message = (catalog as any)[key] || (messages.en as any)[key] || key;

  if (params) {
    for (const [k, v] of Object.entries(params)) {
      message = message.replace(`{${k}}`, String(v));
    }
  }

  return message;
}

/**
 * Set the active locale.
 */
export function setLocale(locale: Locale): void {
  currentLocale = locale;
  if (typeof window !== 'undefined') {
    localStorage.setItem('sentinelgrid_locale', locale);
    document.documentElement.lang = locale;
  }
}

/**
 * Get the current active locale.
 */
export function getLocale(): Locale {
  return currentLocale;
}

/**
 * Initialize locale from storage or browser preference.
 * Call once at app startup.
 */
export function initLocale(): Locale {
  if (typeof window === 'undefined') return DEFAULT_LOCALE;

  const stored = localStorage.getItem('sentinelgrid_locale') as Locale | null;
  if (stored && stored in messages) {
    currentLocale = stored;
    return stored;
  }

  // Check browser language
  const browserLang = navigator.language.split('-')[0] as Locale;
  if (browserLang in messages) {
    currentLocale = browserLang;
    return browserLang;
  }

  return DEFAULT_LOCALE;
}

export { DEFAULT_LOCALE, type Locale, type MessageKey };
