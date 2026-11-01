export const STATUS_STYLE = {
  queued: 'bg-slate-100 text-slate-700',
  processing: 'bg-blue-100 text-blue-700',
  done: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

export function StatusBadge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLE[status] || 'bg-slate-100'}`}>
      {status}
    </span>
  )
}

export function ReviewBadge({ needs }) {
  return needs ? (
    <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
      review needed
    </span>
  ) : null
}

export function Progress({ status }) {
  const pct = { queued: 5, processing: 55, done: 100, failed: 100 }[status] ?? 0
  const color = status === 'failed' ? 'bg-red-500' : status === 'done' ? 'bg-green-500' : 'bg-blue-500'
  return (
    <div className="w-full h-1.5 bg-slate-200 rounded overflow-hidden">
      <div className={`h-full ${color} transition-all`} style={{ width: pct + '%' }} />
    </div>
  )
}