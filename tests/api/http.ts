// tests/api/http.ts
import axios, { AxiosInstance, AxiosHeaders } from 'axios';

function cleanBase(url?: string): string {
  if (!url) throw new Error('WEB_BASE_URL is required');
  return url.replace(/\/+$/, '');
}
function cleanPrefix(prefix: string | undefined, fallback: string): string {
  const p = (prefix ?? fallback).trim();
  return p ? (p.startsWith('/') ? p : `/${p}`) : '';
}

type Opts = { bearer?: string; apiKey?: string; originSecret?: string };

function buildClient(
  prefixEnv: 'API_PREFIX_PUBLIC' | 'API_PREFIX_SECURE',
  fallbackPrefix: string,
  opts?: Opts
): AxiosInstance {
  const base = cleanBase(process.env.WEB_BASE_URL);
  const prefix = cleanPrefix(process.env[prefixEnv], fallbackPrefix);
  const origin = base;

  const instance = axios.create({
    baseURL: `${base}${prefix}`,
    timeout: 10_000,
    validateStatus: () => true,
  });

  instance.interceptors.request.use((cfg) => {
    const headers = AxiosHeaders.from(cfg.headers);

    // Browser-like headers (some WAF rules require these)
    headers.set('Accept', 'application/json');
    headers.set('Content-Type', 'application/json');
    headers.set('Origin', origin);
    headers.set('Referer', origin);
    headers.set('User-Agent', 'Mozilla/5.0 (CI; Playwright-Jest)');

    // Security / origin headers
    if (opts?.originSecret) headers.set('X-Origin-Secret', opts.originSecret);
    if (opts?.apiKey) headers.set('x-api-key', opts.apiKey);
    if (opts?.bearer) headers.set('Authorization', `Bearer ${opts.bearer}`);

    cfg.headers = headers;
    return cfg;
  });

  return instance;
}

export function makeSecureApiClient(bearer: string): AxiosInstance {
  const base = (process.env.WEB_BASE_URL || '').replace(/\/+$/, '');
  const prefix = (process.env.API_PREFIX_SECURE || '/secure/api').replace(/^([^/])/, '/$1');
  const origin = base;

  const inst = axios.create({
    baseURL: `${base}${prefix}`,
    timeout: 10000,
    validateStatus: () => true,
  });

  inst.interceptors.request.use(cfg => {
    const h = AxiosHeaders.from(cfg.headers);
    h.set('Accept', 'application/json');
    h.set('Content-Type', 'application/json');
    h.set('Origin', origin);
    h.set('Referer', origin);
    h.set('Authorization', `Bearer ${bearer}`);
    cfg.headers = h;
    return cfg;
  });

  return inst;
}

export const publicApi = buildClient('API_PREFIX_PUBLIC', '/public/api', {
  originSecret: process.env.CF_ORIGIN_SECRET,
});

export const secureApi = buildClient('API_PREFIX_SECURE', '/secure/api', {
  originSecret: process.env.CF_ORIGIN_SECRET,
  bearer: process.env.SECURE_API_TOKEN,  // optional
});
