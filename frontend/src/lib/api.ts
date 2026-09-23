/**
 * Centralized API configuration and URL resolution for SkySafe AI / WeatherGPT.
 * In development, relative /api paths are proxied via next.config.js rewrites.
 * In production on Vercel, requests either route through Next.js rewrites (BACKEND_URL)
 * or directly to NEXT_PUBLIC_API_URL if configured.
 */

export function getApiBaseUrl(): string {
  // If NEXT_PUBLIC_API_URL is explicitly set, use it (trim trailing slashes)
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '');
  }
  // Otherwise, default to relative path in the browser so Next.js rewrites proxy the call
  return '';
}

export function getApiUrl(path: string): string {
  const base = getApiBaseUrl();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return base ? `${base}${normalizedPath}` : normalizedPath;
}

export function getEventSourceUrl(path: string): string {
  return getApiUrl(path);
}
