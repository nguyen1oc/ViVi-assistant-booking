import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createServer } from 'vite'

let server
let searchFloatingDemoOptions

before(async () => {
  // Use Vite to load the same import.meta.env and module imports as the app.
  server = await createServer({
    configFile: false,
    server: { middlewareMode: true, watch: null, hmr: false },
  })
  ;({ searchFloatingDemoOptions } = await server.ssrLoadModule('/src/api/booking.js'))
})

after(async () => { await server?.close() })

test('disabled demo keeps the backend error instead of reporting an outdated API', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({
    detail: { code: 'FLOATING_DEMO_DISABLED', message: 'Demo đang tắt trên máy chủ.' },
  }), { status: 404 }))

  await assert.rejects(searchFloatingDemoOptions({ vehicleModel: 'VF 9' }), {
    code: 'FLOATING_DEMO_DISABLED', message: 'Demo đang tắt trên máy chủ.', status: 404,
  })
})

test('missing demo route reports the deployment error', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({
    detail: 'Not Found',
  }), { status: 404 }))

  await assert.rejects(searchFloatingDemoOptions({ vehicleModel: 'VF 9' }), {
    code: 'FLOATING_DEMO_API_OUTDATED', status: 404, retryable: false,
  })
})

test('domain 404 errors remain available for showroom fallback', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({
    detail: { code: 'SHOWROOM_NOT_FOUND', message: 'Không tìm thấy showroom.' },
  }), { status: 404 }))

  await assert.rejects(searchFloatingDemoOptions({ vehicleModel: 'VF 9' }), {
    code: 'SHOWROOM_NOT_FOUND', status: 404,
  })
})

test('enabled demo returns availability and sends location to the search API', async (t) => {
  const availability = { showrooms: [{ id: 'showroom-1' }], slots: [] }
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({
    success: true, data: availability,
  }), { status: 200 }))

  const result = await searchFloatingDemoOptions({ vehicleModel: 'VF 9', latitude: 10.77, longitude: 106.70 })

  assert.deepEqual(result, availability)
  const [url, request] = fetchMock.mock.calls[0].arguments
  assert.equal(url, '/api/v1/floating-demo/options')
  assert.equal(request.method, 'POST')
  assert.deepEqual(JSON.parse(request.body), {
    vehicle_model: 'VF 9', showroom_id: '', showroom_query: '', showroom_limit: 12,
    latitude: 10.77, longitude: 106.70,
  })
})
