import { useState } from 'react'
import { api } from '../api'
import { ReviewBadge, StatusBadge } from './ui'

export default function SearchPanel({ onOpen }) {
  const [q, setQ] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async (e) => {
    e.preventDefault()
    if (!q.trim()) return
    setBusy(true)
    setError('')
    try {
      setRes(await api.search(q.trim(), mode))
    } catch (err) {
      setError(err.message)
      setRes(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
      <form onSubmit={run} className="flex flex-wrap gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search documents…"
               className="flex-1 min-w-48 border border-slate-300 rounded px-3 py-2" />
        <select value={mode} onChange={(e) => setMode(e.target.value)}
                className="border border-slate-300 rounded px-2">
          <option value="hybrid">hybrid</option>
          <option value="semantic">semantic</option>
          <option value="keyword">keyword</option>
        </select>
        <button disabled={busy} className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50">
          {busy ? 'Searching…' : 'Search'}
        </button>
      </form>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {res && res.items.length === 0 && <p className="mt-3 text-sm text-slate-500">No matches.</p>}
      {res && (
        <ul className="mt-3 divide-y divide-slate-100">
          {res.items.map((d) => (
            <li key={d.id}>
              <button onClick={() => onOpen(d.id)} className="w-full text-left py-3 hover:bg-slate-50">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">#{d.id} {d.file_name}</span>
                  <StatusBadge status={d.status} />
                  <ReviewBadge needs={d.needs_review} />
                  {d.score != null && (
                    <span className="text-xs text-slate-400">score {d.score.toFixed(3)}</span>
                  )}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {d.invoice_number} · {d.supplier_name} · {d.total} {d.currency}
                </div>
                {d.snippet && (
                  <pre className="mt-1 text-xs text-slate-400 whitespace-pre-wrap line-clamp-2">{d.snippet}</pre>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}