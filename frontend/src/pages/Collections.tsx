import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

interface CardMeta {
  filename: string
  url: string
}

interface Collection {
  name: string
  display_name: string
  source: 'local' | 'firebase'
  image_count: number
  cards?: CardMeta[]
}

export default function Collections() {
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [newName, setNewName] = useState('')
  const [newDisplayName, setNewDisplayName] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [firebaseAvailable, setFirebaseAvailable] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data: Collection[] = await fetch('/api/collections').then(r => r.json())
      setCollections(data)
      setFirebaseAvailable(data.some(c => c.source === 'firebase'))
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    const files = fileInputRef.current?.files
    if (!files || files.length === 0) { setUploadError('Select at least one image file'); return }
    if (!newName.trim()) { setUploadError('Collection name is required'); return }

    setUploading(true)
    setUploadError('')
    setUploadProgress(`Uploading ${files.length} files…`)

    const form = new FormData()
    form.append('display_name', newDisplayName || newName)
    Array.from(files).forEach(f => form.append('files', f))

    try {
      const resp = await fetch(`/api/collections/${encodeURIComponent(newName.trim())}/upload`, {
        method: 'POST',
        body: form,
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(err.detail || 'Upload failed')
      }
      setUploadProgress('')
      setNewName('')
      setNewDisplayName('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      await load()
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed')
      setUploadProgress('')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(name: string) {
    if (!confirm(`Delete collection "${name}" from Firebase Storage? This cannot be undone.`)) return
    try {
      await fetch(`/api/collections/${encodeURIComponent(name)}`, { method: 'DELETE' })
      await load()
    } catch {
      alert('Delete failed')
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-white">🗂️ Card Collections</h1>

      {/* Collections grid */}
      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : collections.length === 0 ? (
        <p className="text-gray-500 text-sm">No collections found.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {collections.map(col => (
            <div key={col.name} className="p-4 bg-[#1a1d27] rounded-xl border border-white/10 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-white">{col.display_name}</p>
                  <p className="text-xs font-mono text-gray-500">{col.name}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    col.source === 'firebase'
                      ? 'border-amber-500/40 text-amber-400 bg-amber-900/20'
                      : 'border-blue-500/40 text-blue-400 bg-blue-900/20'
                  }`}>
                    {col.source === 'firebase' ? '☁️ Firebase' : '💻 Local'}
                  </span>
                </div>
              </div>

              <p className="text-sm text-gray-400">{col.image_count} cards</p>

              {/* Thumbnail strip */}
              {col.cards && col.cards.length > 0 && (
                <div className="flex gap-1 overflow-hidden rounded-lg">
                  {col.cards.slice(0, 6).map(card => (
                    <img
                      key={card.filename}
                      src={card.url}
                      alt={card.filename}
                      className="w-12 h-12 object-cover rounded flex-shrink-0"
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                    />
                  ))}
                  {col.image_count > 6 && (
                    <div className="w-12 h-12 flex items-center justify-center bg-white/5 rounded text-xs text-gray-500 flex-shrink-0">
                      +{col.image_count - 6}
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <Link
                  to={`/collections/${col.name}`}
                  className="flex-1 py-1.5 text-center text-xs font-medium rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-300 hover:bg-violet-600/30 transition-colors"
                >
                  Explore cards
                </Link>
                {col.source === 'firebase' && (
                  <button
                    onClick={() => handleDelete(col.name)}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-900/20 border border-red-500/30 text-red-400 hover:bg-red-900/40 transition-colors"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload new collection */}
      <div className="p-5 bg-[#1a1d27] rounded-xl border border-white/10 space-y-4">
        <div>
          <p className="text-sm font-semibold text-gray-300">Upload New Collection to Firebase</p>
          {!firebaseAvailable && (
            <p className="mt-1 text-xs text-amber-400">
              ⚠ Firebase Storage not configured — set{' '}
              <code className="bg-white/10 px-1 rounded">FIREBASE_STORAGE_BUCKET</code> to enable uploads.
            </p>
          )}
        </div>

        <form onSubmit={handleUpload} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="text-xs text-gray-400">
              Collection slug *
              <input
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="original"
                className="mt-1 w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 font-mono placeholder-gray-600 focus:outline-none focus:border-violet-500"
              />
            </label>
            <label className="text-xs text-gray-400">
              Display name
              <input
                value={newDisplayName}
                onChange={e => setNewDisplayName(e.target.value)}
                placeholder="Original Dixit Deck"
                className="mt-1 w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500"
              />
            </label>
          </div>

          <label className="block text-xs text-gray-400">
            Card images (jpg / png)
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".jpg,.jpeg,.png,.webp"
              className="mt-1 block w-full text-sm text-gray-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:bg-violet-600/30 file:text-violet-300 hover:file:bg-violet-600/50"
            />
          </label>

          {uploadProgress && <p className="text-xs text-blue-400">{uploadProgress}</p>}
          {uploadError && <p className="text-xs text-red-400">{uploadError}</p>}

          <button
            type="submit"
            disabled={uploading || !firebaseAvailable}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white transition-colors"
          >
            {uploading ? 'Uploading…' : '☁️ Upload to Firebase'}
          </button>
        </form>

        <div className="pt-2 border-t border-white/10">
          <p className="text-xs text-gray-500">Or use the CLI tool for bulk uploads:</p>
          <pre className="mt-1 p-2 bg-black/30 rounded text-xs text-gray-400 overflow-x-auto">
            python scripts/upload_collection.py data/1_full --name original
          </pre>
        </div>
      </div>
    </div>
  )
}
