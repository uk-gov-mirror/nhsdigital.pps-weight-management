// tests/api/public.ping.test.ts
import { publicApi } from './http';

it('GET /ping returns 200 + pong', async () => {
  const res = await publicApi.get('/ping', { responseType: 'text' });
  expect(res.status).toBe(200);
  expect((res.data || '').toString().trim().toLowerCase()).toBe('pong');
});
