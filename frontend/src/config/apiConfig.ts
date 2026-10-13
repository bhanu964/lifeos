/**
 * Central API Configuration Module for LifeOS SaaS Frontend
 * 
 * Guarantees:
 * - Dynamic resolution of backend API URL across Local Dev, Vercel Preview, and Production.
 * - Strict trailing slash normalization.
 * - In local development (import.meta.env.DEV), safely defaults to local backend (http://localhost:8000).
 * - In production (import.meta.env.PROD), requires explicit VITE_API_BASE_URL.
 * - Never silently falls back to localhost in production.
 * - Does not expose backend secrets.
 */

const rawEnvUrl = (import.meta.env.VITE_API_BASE_URL || '').trim();
const isDev = Boolean(import.meta.env.DEV);
const isProd = Boolean(import.meta.env.PROD);

function resolveApiBaseUrl(): { url: string; error: string | null } {
  if (rawEnvUrl) {
    // Clean and normalize trailing slashes
    const normalized = rawEnvUrl.replace(/\/+$/, '');
    return { url: normalized, error: null };
  }

  // If running in browser and served from same host (e.g. Render all-in-one container)
  if (typeof window !== 'undefined' && window.location.origin && !window.location.origin.includes('localhost') && !window.location.origin.includes('vercel.app')) {
    return { url: window.location.origin, error: null };
  }

  if (isDev) {
    // Safe default for local development only
    return { url: 'http://localhost:8000', error: null };
  }

  // Production without VITE_API_BASE_URL
  const errorMsg =
    'CRITICAL CONFIGURATION ERROR: VITE_API_BASE_URL is not configured in this production build. ' +
    'Please set VITE_API_BASE_URL to your deployed backend URL in your Vercel Project Settings.';
  
  return {
    url: '',
    error: errorMsg,
  };
}

const resolved = resolveApiBaseUrl();

export const apiConfig = {
  isDev,
  isProd,
  baseUrl: resolved.url,
  configError: resolved.error,

  getBaseUrl(): string {
    if (!resolved.url && isProd) {
      console.error(resolved.error);
      throw new Error(resolved.error || 'Missing VITE_API_BASE_URL');
    }
    return resolved.url;
  },

  isConfigured(): boolean {
    return Boolean(resolved.url);
  },

  getConfigError(): string | null {
    return resolved.error;
  },

  buildUrl(endpoint: string): string {
    const base = this.getBaseUrl();
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${base}${cleanEndpoint}`;
  },

  buildSSEUrl(endpoint: string, queryParams: Record<string, string> = {}): string {
    const fullUrl = this.buildUrl(endpoint);
    const searchParams = new URLSearchParams();
    for (const [key, val] of Object.entries(queryParams)) {
      if (val !== undefined && val !== null && val !== '') {
        searchParams.append(key, val);
      }
    }
    const qs = searchParams.toString();
    return qs ? `${fullUrl}?${qs}` : fullUrl;
  },
};
