import { useEffect, useState } from 'react'
import { api } from '../api'
import { Progress, ReviewBadge, StatusBadge } from './ui'

export default function DocumentList({ refreshKey, onOpen }) {
  const [items, setItems] = useState([])
  const [status, setStatus] = useState('')
  const [review, setReview] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let stop = false
    const load = async () => {
      try {
        const data = await api.list({ status, needs_review: review, limit: 100 })
        if (!stop) { setItems(data.items); setError('') }
      } catch (e) {
        if (!stop) setError(e.message)
      }
    }
    load()
    const t = setInterval(load, 2000)
    return () => { stop = true; clearInterval(t) }
  }, [status, review, refreshKey])

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200">
      <div className="flex flex-wrap items-center gap-3 p-4 border-b border-slate-200">
        <h2 className="font-semibold mr-auto">Documents</h2>
        <select value={status} onChange={(e) => setStatus(e.target.value)}
                className="border border-slate-300 rounded px-2 py-1 text-sm">
          <option value="">all statuses</option>
          <option value="queued">queued</option>
          <option value="processing">processing</option>
          <option value="done">done</option>
          <option value="failed">failed</option>
        </select>
        <select value={review} onChange={(e) => setReview(e.target.value)}
                className="border border-slate-300 rounded px-2 py-1 text-sm">
          <option value="">review: any</option>
          <option value="true">needs review</option>
          <option value="false">clean</option>
        </select>
      </div>
      {error && <p className="p-4 text-sm text-red-600">Cannot reach API: {error}</p>}
      {!error && items.length === 0 && (
        <p className="p-6 text-sm text-slate-500">No documents yet. Upload some above.</p>
      )}
      <ul className="divide-y divide-slate-100">
        {items.map((d) => (
          <li key={d.id}>
            <button onClick={() => onOpen(d.id)}
                    className="w-full text-left p-4 hover:bg-slate-50 flex flex-col gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium">#{d.id} {d.file_name}</span>
                <StatusBadge status={d.status} />
                <ReviewBadge needs={d.needs_review} />
              </div>
              <Progress status={d.status} />
              <div className="text-xs text-slate-500 flex gap-4 flex-wrap">
                {d.invoice_number && <span>Invoice: {d.invoice_number}</span>}
                {d.supplier_name && <span>Supplier: {d.supplier_name}</span>}
                {d.total != null && <span>Total: {d.total} {d.currency || ''}</span>}
                {d.error && <span className="text-red-600">{d.error}</span>}
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}