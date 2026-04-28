let _sessionToken = null

export function setSessionToken(t) {
  _sessionToken = t
}

export async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) }
  if (opts.method && opts.method !== 'GET' && _sessionToken) {
    headers['X-Attune-Client'] = _sessionToken
  }
  const res = await fetch(path, { ...opts, headers })
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
}
