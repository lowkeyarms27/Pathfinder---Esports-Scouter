const BASE    = import.meta.env.VITE_BACKEND_URL || ''
const API_KEY = import.meta.env.VITE_API_KEY || ''

function authHeaders(extra = {}) {
  return API_KEY ? { 'x-api-key': API_KEY, ...extra } : extra
}

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    ...opts,
    headers: { ...authHeaders(), ...(opts.headers || {}) },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function submitScout(formData) {
  const res = await fetch(BASE + '/api/scout', {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}

export async function submitScoutMulti(formData) {
  const res = await fetch(BASE + '/api/scout/multi', {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}

export async function getStatus(sid)   { return req(`/api/status/${sid}`) }
export async function getLog(sid)      { return req(`/api/log/${sid}`) }
export async function getResults(sid)  { return req(`/api/results/${sid}`) }
export async function getSessions(limit = 100) { return req(`/api/sessions?limit=${limit}`) }
export async function getArchetypes()  { return req('/api/archetypes') }
