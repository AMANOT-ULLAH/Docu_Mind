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

export function Progress({ status, stage, done, total }) {
  let pct = 0
  let label = ''
  let color = 'bg-blue-500'
  let pulse = false

  if (status === 'queued') {
    pct = 3; label = 'Waiting in queue…'; color = 'bg-slate-400'
  } else if (status === 'processing') {
    if (stage === 'extracting') {
      pct = 92; label = `All ${total} pages read. AI is extracting data…`; pulse = true
    } else if (total) {
      pct = Math.round((90 * (done || 0)) / total)
      label = `Reading pages ${done || 0} / ${total}`
    } else {
      pct = 15; label = 'Processing…'; pulse = true
    }
  } else if (status === 'done') {
    pct = 100; color = 'bg-green-500'
  } else if (status === 'failed') {
    pct = 100; color = 'bg-red-500'
  }

  return (
    <div className="w-full">
      <div className="w-full h-2 bg-slate-200 rounded overflow-hidden">
        <div className={`h-full ${color} transition-all duration-500 ${pulse ? 'animate-pulse' : ''}`}
             style={{ width: pct + '%' }} />
      </div>
      {label && <p className="mt-1 text-xs text-slate-500">{label}</p>}
    </div>
  )
}