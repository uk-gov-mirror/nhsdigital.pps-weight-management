import axios from 'axios';

describe('Health endpoint', () => {
  it('GET /health returns 200 + "ok"', async () => {
    const base = (process.env.DJANGO_BASE_URL || '').replace(/\/+$/, '');
    if (!base) throw new Error('DJANGO_BASE_URL is required');

    const res = await axios.get(`${base}/health`, { responseType: 'text', validateStatus: () => true });
    expect(res.status).toBe(200);
    expect((res.data || '').toString().trim().toLowerCase()).toBe('ok');
  });
});
