// tests/api/secure.items.test.ts
import axios from 'axios';
import { getAccessTokenWithPassword } from './cognito-auth';
import { makeSecureApiClient } from './http';

/**
 * Extracts the stored value from either:
 *  - plain text:   "testing"
 *  - JSON object:  { value: "testing" }  (or legacy shapes)
 */
function extractValue(body: any): string {
  if (body == null) return '';
  if (typeof body === 'string') return body.trim();
  if (body instanceof Buffer) return body.toString('utf8').trim();

  const candidates = [
    body?.value,
    body?.status,
    body?.Item?.value,
    body?.item?.value,
    body?.Attributes?.value,
  ].filter(v => typeof v === 'string');

  return (candidates[0] ?? '').trim();
}

describe('Secure Item API (Postgres-backed)', () => {
  const id = 123;                 // numeric path param (Django <int:item_id>)
  const value = 'testing';
  let api: ReturnType<typeof makeSecureApiClient>;
  let secureBase: string;

  beforeAll(async () => {
    // Build the secure base URL in the same way your helpers do
    const base = (process.env.DJANGO_BASE_URL ?? 'http://localhost:8000').replace(/\/+$/, '');
    const securePrefix = process.env.API_PREFIX_SECURE ?? '/secure/api';
    secureBase = `${base}${securePrefix}`;

    const token = await getAccessTokenWithPassword();
    api = makeSecureApiClient(token);
  });

  it('POST /secure/api/item/:id upserts a record', async () => {
    const res = await api.post(`/item/${id}`, { value });
    expect([200, 201]).toContain(res.status);
  });

  it('GET /secure/api/item/:id returns the stored value', async () => {
    const res = await api.get(`/item/${id}`);
    expect(res.status).toBe(200);

    const got = extractValue(res.data);
    if (got !== value) {
      // eslint-disable-next-line no-console
      console.error('Unexpected body:', typeof res.data, JSON.stringify(res.data, null, 2));
    }
    expect(got).toBe(value);
  });

  // Unauthorized when NO token is provided
  it('GET /secure/api/item/:id without a token is unauthorized', async () => {
    const anon = axios.create({
      baseURL: secureBase,
      // don't throw on 4xx so we can assert the status
      validateStatus: () => true,
    });

    const res = await anon.get(`/item/${id}`);
    expect([401, 403]).toContain(res.status);
  });

  // Unauthorized when an INVALID token is provided
  it('GET /secure/api/item/:id with an invalid token is unauthorized', async () => {
    const bad = makeSecureApiClient('this.is.not.a.valid.jwt');
    const res = await bad.get(`/item/${id}`).catch((e: any) => e.response ?? e);
    expect([401, 403]).toContain(res.status);
  });
});
