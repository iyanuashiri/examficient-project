const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export function getToken() {
  return localStorage.getItem('examficient_token')
}

export function setToken(token) {
  localStorage.setItem('examficient_token', token)
}

export function clearToken() {
  localStorage.removeItem('examficient_token')
}

export async function apiFetch(path, options = {}) {
  const { method = 'GET', body, auth = true, form = false, raw = false, timeoutMs = 20000 } = options
  const headers = {}
  let payload
  if (body !== undefined) {
    if (form) {
      payload = new URLSearchParams(body)
    } else if (raw) {
      payload = body // e.g. FormData: browser sets Content-Type itself
    } else {
      headers['Content-Type'] = 'application/json'
      payload = JSON.stringify(body)
    }
  }
  if (auth) {
    const token = getToken()
    if (!token) {
      const err = new Error('Not authenticated')
      err.status = 401
      throw err
    }
    headers['Authorization'] = `Bearer ${token}`
  }
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  let res
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: payload, signal: ctrl.signal })
  } catch (e) {
    clearTimeout(timer)
    if (e && e.name === 'AbortError') {
      const err = new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s — the server may be down. Check the backend terminal, then retry.`)
      err.status = 0
      throw err
    }
    throw e
  }
  clearTimeout(timer)
  if (res.status === 401 && auth) {
    clearToken()
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch {
      // keep default
    }
    const err = new Error(detail)
    err.status = res.status
    throw err
  }
  if (res.status === 204) return null
  return res.json()
}
