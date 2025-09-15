// tests/api/secure.items.test.ts
import { getAccessTokenWithPassword } from './cognito-auth';
import { makeSecureApiClient } from './http';

function extractFromDdb(body: any) {
  // Accept: { pk:{S}, status:{S}, ... } OR { Item: { ... } } OR { Attributes: { ... } }
  const src = body?.Item ?? body?.item ?? body?.Attributes ?? body ?? {};

  const getS = (k: string) =>
    src?.[k]?.S ?? src?.[k]?.s ?? (typeof src?.[k] === 'string' ? src[k] : undefined);

  const pk = getS('pk');
  const sk = getS('sk');
  const rawId = pk ?? sk ?? '';
  const id = rawId.includes('#') ? rawId.split('#').pop() : rawId;

  const status = (getS('status') ?? '').toLowerCase();

  return { id, status };
}

describe('Secure Items API', () => {
  const id = '123';
  const status = 'testing';
  let api: ReturnType<typeof makeSecureApiClient>;

  beforeAll(async () => {
    const token = await getAccessTokenWithPassword();
    api = makeSecureApiClient(token);
  });

  it('POST /secure/api/items/ stores a record', async () => {
    const res = await api.post('/items/', { id, status });
    expect([200, 201]).toContain(res.status);
  });

  it('GET /secure/api/items/:id returns correct id and status', async () => {
    const res = await api.get(`/items/${id}`);
    expect(res.status).toBe(200);

    const { id: gotId, status: gotStatus } = extractFromDdb(res.data);

    // Helpful debug if it doesn’t match
    if (gotId !== id || gotStatus !== status) {
      // eslint-disable-next-line no-console
      console.error('Unexpected body:', JSON.stringify(res.data, null, 2));
    }

    expect(gotId).toBe(id);
    expect(gotStatus).toBe(status);
  });
});
