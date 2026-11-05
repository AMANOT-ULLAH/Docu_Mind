import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { Progress, ReviewBadge, StatusBadge } from './ui'

const FIELDS = [
  ['invoice_number', 'Invoice number'], ['invoice_date', 'Invoice date'],
  ['supplier_name', 'Supplier'], ['customer_name', 'Customer'],
  ['subtotal', 'Subtotal'], ['tax', 'Tax'], ['total', 'Total'], ['currency', 'Currency'],
]
const NUMERIC = new Set(['subtotal', 'tax', 'total'])
const CONF = { high: 'text-green-700', medium: 'text-amber-700', low: 'text-red-700' }

export default function DocumentDetail({ id, onBack }) {
  const [info, setInfo] = useState(null)
  const [res, setRes] = useState(null)
  const [edits, setEdits] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const d = await api.detail(id)
      setInfo(d)
      if (d.status === 'done') setRes(await api.result(id))
      else setRes(null)
      setError('')
    } catch (e) {
      setError(e.message)
    }
  }, [id])

  useEffect(() => {
    load()
    const t = setInterval(() => {
      if (!info || info.status === 'queued' || info.status === 'processing') load()
    }, 2000)
    return () => clearInterval(t)
  }, [load, info?.status])

  const eff = res?.effective

  const save = async () => {
    const fields = {}
    for (const [k, raw] of Object.entries(edits)) {
      if (raw === '') fields[k] = null
      else if (NUMERIC.has(k)) {
        const n = Number(raw.replace(/,/g, ''))
        if (Number.isNaN(n)) { setError(`${k} must be a number`); return }
        fields[k] = n
      } else fields[k] = raw
    }
    if (!Object.keys(fields).length) return
    setBusy(true)
    try {
      setRes(await api.correct(id, fields))
      setEdits({})
      setError('')
      setInfo(await api.detail(id))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const act = async (fn) => {
    setBusy(true)
    try { await fn(); await load() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  if (!info) {
    return <div className="p-6">{error ? <p className="text-red-600">{error}</p> : 'Loading…'}</div>
  }

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="text-sm text-blue-600 hover:underline">← Back</button>
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4 space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <h2 className="text-lg font-semibold">#{info.id} {info.file_name}</h2>
          <StatusBadge status={info.status} />
          <ReviewBadge needs={info.needs_review} />
        </div>
                <Progress status={info.status} stage={info.stage} done={info.pages_done} total={info.pages_total} />
        {info.error && <p className="text-sm text-red-600">{info.error}</p>}
        <div className="flex gap-2">
          {info.status === 'failed' && (
            <button disabled={busy} onClick={() => act(() => api.reprocess(id))}
                    className="px-3 py-1.5 bg-slate-800 text-white rounded text-sm disabled:opacity-50">
              Reprocess
            </button>
          )}
          {info.status === 'done' && info.needs_review && (
            <button disabled={busy} onClick={() => act(() => api.approve(id))}
                    className="px-3 py-1.5 bg-green-600 text-white rounded text-sm disabled:opacity-50">
              Approve as reviewed
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {res && eff && (
        <>
          <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
            <h3 className="font-semibold mb-3">
              Extracted data {res.corrected && <span className="text-xs text-slate-500">(manually corrected)</span>}
            </h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-1 pr-3">Field</th><th className="pr-3">Value</th>
                  <th className="pr-3">Confidence</th><th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {FIELDS.map(([k, label]) => {
                  const f = eff[k] || {}
                  const edited = k in edits
                  return (
                    <tr key={k} className="border-t border-slate-100 align-top">
                      <td className="py-2 pr-3 text-slate-600">{label}</td>
                      <td className="pr-3">
                        <input
                          value={edited ? edits[k] : (f.value ?? '')}
                          placeholder={f.value == null ? '(missing)' : ''}
                          onChange={(e) => setEdits({ ...edits, [k]: e.target.value })}
                          className={`border rounded px-2 py-1 w-48 ${edited ? 'border-blue-500' : 'border-slate-300'}`} />
                      </td>
                      <td className={`pr-3 ${CONF[f.confidence] || ''}`}>
                        {f.value != null ? f.confidence : '—'}
                      </td>
                      <td className="text-xs text-slate-500">{f.evidence || ''}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            <div className="mt-3 flex gap-2">
              <button disabled={busy || !Object.keys(edits).length} onClick={save}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm disabled:opacity-40">
                Save corrections
              </button>
              {Object.keys(edits).length > 0 && (
                <button onClick={() => setEdits({})} className="px-3 py-1.5 text-sm text-slate-600">
                  Discard
                </button>
              )}
            </div>
            <p className="mt-2 text-xs text-slate-400">
              Saving re-runs validation and duplicate checks. The original AI answer is kept unchanged.
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
            <h3 className="font-semibold mb-3">Line items ({eff.line_items?.length || 0})</h3>
            {eff.line_items?.length ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500">
                    <th className="py-1">Description</th><th>Qty</th><th>Unit price</th><th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {eff.line_items.map((li, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="py-1">{li.description}</td>
                      <td>{li.quantity ?? '—'}</td><td>{li.unit_price ?? '—'}</td><td>{li.amount ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-sm text-slate-500">No line items found.</p>}
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
            <h3 className="font-semibold mb-3">Validation issues ({res.issues.length})</h3>
            {res.issues.length === 0 && <p className="text-sm text-green-700">No issues.</p>}
            <ul className="space-y-2">
              {res.issues.map((i) => (
                <li key={i.id}
                    className={`text-sm p-2 rounded border-l-4 ${i.severity === 'error'
                      ? 'bg-red-50 border-red-500' : 'bg-amber-50 border-amber-500'}`}>
                  <span className="font-medium">{i.type}</span>
                  <span className="text-slate-500"> · {i.field}</span>
                  <div>{i.message}</div>
                  {(i.expected || i.actual) && (
                    <div className="text-xs text-slate-500">
                      {i.expected && <>expected {i.expected} </>}{i.actual && <>actual {i.actual}</>}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
        <h3 className="font-semibold mb-3">Processing history</h3>
        <ul className="text-sm space-y-1">
          {info.events.map((e, i) => (
            <li key={i} className="flex gap-3">
              <span className="text-slate-400 w-44 shrink-0">{new Date(e.at).toLocaleString()}</span>
              <span className="font-medium">{e.event}</span>
              <span className="text-slate-500">{e.message}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}