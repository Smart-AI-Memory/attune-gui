let _sessionToken = null

export function setSessionToken(t) {
  _sessionToken = t
}

// In-flight dedup for GET requests: same URL → same promise.
const _inflight = new Map()

export async function api(path, opts = {}) {
  const isGet = !opts.method || opts.method === 'GET'

  if (isGet && _inflight.has(path)) {
    return _inflight.get(path)
  }

  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) }
  if (opts.method && opts.method !== 'GET' && _sessionToken) {
    headers['X-Attune-Client'] = _sessionToken
  }

  const promise = fetch(path, { ...opts, headers })
    .then(async (res) => {
      if (!res.ok) {
        let body
        const text = await res.text()
        try { body = JSON.parse(text) } catch { body = { detail: text } }
        const msg = body?.detail?.message || body?.detail || `HTTP ${res.status}`
        const err = new Error(msg)
        err.status = res.status
        throw err
      }
      return res.json()
    })
    .finally(() => {
      if (isGet) _inflight.delete(path)
    })

  if (isGet) _inflight.set(path, promise)

  return promise
}
