import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SkySafe AI - Disaster Action Intelligence',
  description: 'Multilingual voice/SMS action intelligence layer for official weather warnings.',
  manifest: '/manifest.json',
};

export const viewport: Viewport = {
  themeColor: '#1e3a8a',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#1e3a8a" />
      </head>
      <body className="antialiased flex flex-col min-h-screen text-slate-100 bg-slate-900 selection:bg-blue-600">
        {/* DRILL / SIMULATION Banner */}
        <div className="bg-amber-500 text-slate-950 px-4 py-1.5 text-center font-bold text-xs uppercase tracking-wider shadow-md">
          ⚠️ DRILL / SIMULATION MODE — SIH 2026 PROTOTYPE
        </div>
        
        <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50 px-4 py-3">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🌩️</span>
              <span className="font-extrabold text-xl tracking-tight text-white">SkySafe <span className="text-blue-500">AI</span></span>
            </div>
            <span className="text-xs font-semibold px-2 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
              SIH26068
            </span>
          </div>
        </header>

        <main className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6">
          {children}
        </main>

        <footer className="border-t border-slate-800 bg-slate-950/40 text-slate-400 text-xs text-center py-4 px-4">
          <p>© 2026 SkySafe AI — Disaster Management Action Intelligence</p>
        </footer>

        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js').then(
                    function(registration) {
                      console.log('SkySafe ServiceWorker registered:', registration.scope);
                    },
                    function(err) {
                      console.log('SkySafe ServiceWorker registration failed:', err);
                    }
                  );
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
