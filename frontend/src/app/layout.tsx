import type { Metadata } from 'next';
import { DM_Sans, IBM_Plex_Sans, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { QueryProvider } from '@/lib/providers/QueryProvider';
import { AuthProvider } from '@/lib/providers/AuthProvider';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider } from '@/lib/providers/ThemeProvider';
import themeConfig from '../../theme.config.json';

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
  weight: ['400', '500', '600', '700'],
});

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
  weight: ['400', '500', '600'],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'SentinelGrid | Developer source preview',
  description: 'Experimental security operations source for architecture review and developer feedback.',
  icons: {
    icon: '/icon.svg',
    shortcut: '/icon.svg',
    apple: '/icon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const defaultTheme =
    (themeConfig as any)?.defaultTheme === 'light'
      ? 'light'
      : (themeConfig as any)?.defaultTheme === 'system'
      ? 'system'
      : 'dark';

  const themeInitScript = `(function(){try{var stored=localStorage.getItem('sentinelgrid_theme');var cfg='${defaultTheme}';var choice=stored||cfg;var prefersDark=window.matchMedia('(prefers-color-scheme: dark)').matches;var resolved=choice==='system'?(prefersDark?'dark':'light'):choice;var targets=[document.documentElement,document.body];var apply=function(el){if(!el)return;if(resolved==='dark'){el.classList.add('dark');el.setAttribute('data-theme','dark');}else{el.classList.remove('dark');el.setAttribute('data-theme','light');}};targets.forEach(apply);document.addEventListener('DOMContentLoaded',function(){apply(document.body);});}catch(e){}})();`;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className={`${dmSans.variable} ${ibmPlexSans.variable} ${jetbrainsMono.variable} ${ibmPlexSans.className}`}>
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              <aside className="border-b border-border-muted bg-surface-card px-4 py-2 text-center text-sm text-text-muted">
                Developer source preview. Product flows are experimental; no hosted service or production certification is offered.
              </aside>
              {children}
              <Toaster position="top-right" />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
