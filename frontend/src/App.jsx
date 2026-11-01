import { useState } from 'react'
import DocumentDetail from './components/DocumentDetail'
import DocumentList from './components/DocumentList'
import SearchPanel from './components/SearchPanel'
import UploadBox from './components/UploadBox'

export default function App() {
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('documents')
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-6">
          <h1 className="text-xl font-bold">DocuMind</h1>
          <nav className="flex gap-4 text-sm">
            {['documents', 'search'].map((t) => (
              <button key={t} onClick={() => { setTab(t); setSelected(null) }}
                      className={tab === t ? 'font-semibold text-blue-600' : 'text-slate-600'}>
                {t === 'documents' ? 'Documents' : 'Search'}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-6 space-y-4">
        {selected ? (
          <DocumentDetail id={selected} onBack={() => setSelected(null)} />
        ) : tab === 'documents' ? (
          <>
            <UploadBox onUploaded={() => setRefreshKey((k) => k + 1)} />
            <DocumentList refreshKey={refreshKey} onOpen={setSelected} />
          </>
        ) : (
          <SearchPanel onOpen={setSelected} />
        )}
      </main>
    </div>
  )
}