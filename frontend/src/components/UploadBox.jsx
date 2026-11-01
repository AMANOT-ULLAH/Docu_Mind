import { useRef, useState } from 'react'
import { api } from '../api'

const ACCEPT = '.pdf,.jpg,.jpeg,.png,.tif,.tiff,.xlsx,.xls,.csv'

export default function UploadBox({ onUploaded }) {
  const input = useRef(null)
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const send = async (fileList) => {
    const files = Array.from(fileList)
    if (!files.length) return
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.upload(files)
      const rejected = r.documents.filter((d) => d.status === 'rejected')
      setMsg({
        ok: rejected.length === 0,
        text: `${r.documents.length - rejected.length} queued` +
          (rejected.length ? `, rejected: ${rejected.map((d) => `${d.file_name} (${d.error})`).join('; ')}` : ''),
      })
      onUploaded()
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); send(e.dataTransfer.files) }}
      className={`border-2 border-dashed rounded-lg p-8 text-center bg-white transition
        ${drag ? 'border-blue-500 bg-blue-50' : 'border-slate-300'}`}
    >
      <p className="text-slate-600 mb-3">Drag and drop invoices here (PDF, JPG, PNG, TIFF, XLSX, XLS, CSV)</p>
      <input ref={input} type="file" multiple accept={ACCEPT} className="hidden"
             onChange={(e) => send(e.target.files)} />
      <button onClick={() => input.current.click()} disabled={busy}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
        {busy ? 'Uploading…' : 'Choose files'}
      </button>
      {msg && <p className={`mt-3 text-sm ${msg.ok ? 'text-green-700' : 'text-red-600'}`}>{msg.text}</p>}
    </div>
  )
}