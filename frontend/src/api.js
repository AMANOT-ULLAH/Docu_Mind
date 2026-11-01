const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function req(path, opts = {}) {
  const r = await fetch(BASE + path, opts)
  let body = null
  try { body = await r.json() } catch { /* খালি উত্তর */ }
  if (!r.ok) {
    const d = body && body.detail
    const msg = typeof d === 'string' ? d : JSON.stringify(d || body || r.statusText)
    throw new Error(msg)
  }
  return body
}

const json = (method, data) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
})

export const api = {
  upload: (files) => {
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    return req('/documents', { method: 'POST', body: fd })
  },
  list: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null)
    ).toString()
    return req('/documents' + (qs ? '?' + qs : ''))
  },
  detail: (id) => req(`/documents/${id}`),
  result: (id) => req(`/documents/${id}/result`),
  correct: (id, fields, line_items) =>
    req(`/documents/${id}/result`, json('PATCH', line_items ? { fields, line_items } : { fields })),
  approve: (id) => req(`/documents/${id}/approve`, { method: 'POST' }),
  reprocess: (id) => req(`/documents/${id}/reprocess`, { method: 'POST' }),
  search: (q, mode) => req(`/search?q=${encodeURIComponent(q)}&mode=${mode}`),
}