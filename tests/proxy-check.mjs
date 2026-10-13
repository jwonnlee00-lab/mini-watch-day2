import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../monitor/next-frontend/app/api/[...path]/route.js', import.meta.url), 'utf8');
const route = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const originalFetch = globalThis.fetch;
const originalBase = process.env.MONITOR_API_URL;
const context = { params: Promise.resolve({ path: ['auth', 'login'] }) };
try {
  delete process.env.MONITOR_API_URL;
  let response = await route.POST(new Request('http://localhost/api/auth/login', { method: 'POST' }), context);
  assert.equal(response.status, 503);
  console.log('PASS missing MONITOR_API_URL returns 503');
  process.env.MONITOR_API_URL = 'http://monitor.invalid';
  globalThis.fetch = async () => { throw new Error('offline'); };
  response = await route.POST(new Request('http://localhost/api/auth/login', { method: 'POST' }), context);
  assert.equal(response.status, 502);
  console.log('PASS upstream connection failure returns 502');
  let received;
  globalThis.fetch = async (target, options) => {
    received = { target, options };
    const headers = new Headers({ 'Content-Type': 'application/json' });
    headers.append('Set-Cookie', 'first=test; HttpOnly; Path=/');
    headers.append('Set-Cookie', 'second=test; Secure; Path=/');
    return new Response('{"error":"unauthorized"}', { status: 401, headers });
  };
  response = await route.POST(new Request('http://localhost/api/auth/login?test=1', {
    method: 'POST', headers: { Cookie: 'session=test', 'X-CSRF-Token': 'test-csrf',
                             'Content-Type': 'application/json' }, body: '{"username":"test"}',
  }), context);
  assert.equal(response.status, 401);
  assert.equal(received.options.headers.get('cookie'), 'session=test');
  assert.equal(received.options.headers.get('x-csrf-token'), 'test-csrf');
  assert.equal(received.target.search, '?test=1');
  assert.equal(Buffer.from(received.options.body).toString(), '{"username":"test"}');
  assert.equal(response.headers.getSetCookie().length, 2);
  console.log('PASS Cookie/CSRF/body/query/status and multiple Set-Cookie forwarding');
} finally {
  globalThis.fetch = originalFetch;
  if (originalBase === undefined) delete process.env.MONITOR_API_URL;
  else process.env.MONITOR_API_URL = originalBase;
}
