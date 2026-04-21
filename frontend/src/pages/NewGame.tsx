import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface PromptStyle {
  id: string
  name: string
  description: string
}

interface ModelOption {
  id: string
  name: string
}

interface CollectionOption {
  name: string
  display_name: string
  source: string
  image_count: number
}

interface PlayerRow {
  model: string
  name: string
  prompt_style: string
}

const FALLBACK_MODELS: ModelOption[] = [
  { id: 'openai/gpt-4o', name: 'openai/gpt-4o' },
  { id: 'openai/gpt-4o-mini', name: 'openai/gpt-4o-mini' },
  { id: 'anthropic/claude-sonnet-4.6', name: 'anthropic/claude-sonnet-4.6' },
  { id: 'anthropic/claude-haiku-4.5', name: 'anthropic/claude-haiku-4.5' },
  { id: 'google/gemini-2.5-flash', name: 'google/gemini-2.5-flash' },
  { id: 'google/gemini-2.0-flash-001', name: 'google/gemini-2.0-flash-001' },
  { id: 'meta-llama/llama-4-maverick', name: 'meta-llama/llama-4-maverick' },
  { id: 'meta-llama/llama-4-scout', name: 'meta-llama/llama-4-scout' },
  { id: 'x-ai/grok-4', name: 'x-ai/grok-4' },
  { id: 'mistralai/pixtral-large-2411', name: 'mistralai/pixtral-large-2411' },
  { id: 'qwen/qwen-vl-plus', name: 'qwen/qwen-vl-plus' },
]

const STYLE_SHORT: Record<string, string> = {
  creative: '✨',
  deceptive: '🎭',
  minimalist: '◾',
  narrative: '📖',
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

export default function NewGame() {
  const navigate = useNavigate()
  const [styles, setStyles] = useState<PromptStyle[]>([])
  const [models, setModels] = useState<ModelOption[]>(FALLBACK_MODELS)
  const [collections, setCollections] = useState<CollectionOption[]>([])
  const [players, setPlayers] = useState<PlayerRow[]>([
    { model: 'openai/gpt-4o', name: '', prompt_style: 'creative' },
    { model: 'anthropic/claude-sonnet-4.6', name: '', prompt_style: 'creative' },
    { model: 'google/gemini-2.5-flash', name: '', prompt_style: 'creative' },
    { model: 'meta-llama/llama-4-maverick', name: '', prompt_style: 'creative' },
  ])
  const [maxRounds, setMaxRounds] = useState(10)
  const [scoreToWin, setScoreToWin] = useState(30)
  const [selectedCollection, setSelectedCollection] = useState('data/1_full')
  const [useCache, setUseCache] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/prompt-styles').then(r => r.json()).then(setStyles)
    fetch('/api/models').then(r => r.json()).then(setModels).catch(() => {/* keep fallback */})
    fetch('/api/collections')
      .then(r => r.json())
      .then((cols: CollectionOption[]) => {
        setCollections(cols)
        if (cols.length > 0) setSelectedCollection(cols[0].name)
      })
      .catch(() => {/* keep default */})
  }, [])

  function addPlayer() {
    const nextModel = FALLBACK_MODELS[players.length % FALLBACK_MODELS.length].id
    setPlayers(p => [...p, { model: nextModel, name: '', prompt_style: 'creative' }])
  }

  function removePlayer(i: number) {
    setPlayers(p => p.filter((_, j) => j !== i))
  }

  function updatePlayer(i: number, field: keyof PlayerRow, value: string) {
    setPlayers(p => p.map((row, j) => j === i ? { ...row, [field]: value } : row))
  }

  function randomize() {
    const styleIds = styles.length > 0 ? styles.map(s => s.id) : ['creative', 'deceptive', 'minimalist', 'narrative']
    const availableModels = models.length > 0 ? models : FALLBACK_MODELS
    const count = 4 + Math.floor(Math.random() * 3) // 4–6
    const newPlayers: PlayerRow[] = Array.from({ length: count }, () => ({
      model: pick(availableModels).id,
      name: '',
      prompt_style: pick(styleIds),
    }))
    setPlayers(newPlayers)
  }

  async function startGame(e: React.FormEvent) {
    e.preventDefault()
    if (players.length < 2) { setError('Need at least 2 players'); return }
    if (players.some(p => !p.model.trim())) { setError('All players need a model'); return }

    setSubmitting(true)
    setError('')
    try {
      const resp = await fetch('/api/games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          players: players.map(p => ({
            model: p.model.trim(),
            name: p.name.trim() || undefined,
            prompt_style: p.prompt_style,
          })),
          prompt_style: 'creative', // global fallback (overridden per-player)
          max_rounds: maxRounds,
          score_to_win: scoreToWin,
          image_directory: selectedCollection,
          use_cache: useCache,
        }),
      })
      const data = await resp.json()
      navigate(data.live_url)
    } catch (err) {
      setError('Failed to start game. Is the server running?')
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">🎮 New Game</h1>

      <form onSubmit={startGame} className="space-y-6">

        {/* Players */}
        <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-300">Players ({players.length})</p>
            <button
              type="button"
              onClick={randomize}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-300 hover:bg-amber-500/30 hover:border-amber-400/60 transition-all"
            >
              🎲 Randomize
            </button>
          </div>

          {/* Column headers */}
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-2 px-1">
            <span className="text-xs text-gray-600">Model</span>
            <span className="text-xs text-gray-600 w-28 text-center">Style</span>
            <span className="text-xs text-gray-600 w-28">Name</span>
            <span className="w-6" />
          </div>

          {players.map((p, i) => (
            <div key={i} className="grid grid-cols-[1fr_auto_auto_auto] gap-2 items-center">
              <select
                value={p.model}
                onChange={e => updatePlayer(i, 'model', e.target.value)}
                className="w-full px-3 py-2 bg-[#12141e] border border-white/10 rounded-lg text-sm text-gray-200 font-mono focus:outline-none focus:border-violet-500"
              >
                {models.map(m => (
                  <option key={m.id} value={m.id}>{m.id}</option>
                ))}
              </select>

              <select
                value={p.prompt_style}
                onChange={e => updatePlayer(i, 'prompt_style', e.target.value)}
                title={styles.find(s => s.id === p.prompt_style)?.name ?? p.prompt_style}
                className="w-28 px-2 py-2 bg-[#12141e] border border-white/10 rounded-lg text-xs text-gray-300 focus:outline-none focus:border-violet-500"
              >
                {(styles.length > 0 ? styles : [
                  { id: 'creative', name: 'Creative' },
                  { id: 'deceptive', name: 'Deceptive' },
                  { id: 'minimalist', name: 'Minimalist' },
                  { id: 'narrative', name: 'Narrative' },
                ]).map(s => (
                  <option key={s.id} value={s.id}>
                    {STYLE_SHORT[s.id] ?? ''} {s.name}
                  </option>
                ))}
              </select>

              <input
                value={p.name}
                onChange={e => updatePlayer(i, 'name', e.target.value)}
                placeholder="name (opt)"
                className="w-28 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500"
              />
              <button
                type="button"
                onClick={() => removePlayer(i)}
                disabled={players.length <= 2}
                className="px-2 text-gray-600 hover:text-red-400 disabled:opacity-20"
              >✕</button>
            </div>
          ))}
          <button
            type="button"
            onClick={addPlayer}
            className="text-sm text-violet-400 hover:text-violet-300"
          >+ Add Player</button>
        </div>

        {/* Game Settings */}
        <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10 space-y-3">
          <p className="text-sm font-semibold text-gray-300">Game Settings</p>
          <div className="grid grid-cols-2 gap-4">
            <label className="text-xs text-gray-400">
              Max Rounds
              <input
                type="number" min={1} max={50} value={maxRounds}
                onChange={e => setMaxRounds(+e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-violet-500"
              />
            </label>
            <label className="text-xs text-gray-400">
              Score to Win
              <input
                type="number" min={5} max={100} value={scoreToWin}
                onChange={e => setScoreToWin(+e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-violet-500"
              />
            </label>
          </div>
          <label className="text-xs text-gray-400">
            Card Collection
            {collections.length > 0 ? (
              <select
                value={selectedCollection}
                onChange={e => setSelectedCollection(e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-[#12141e] border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-violet-500"
              >
                {collections.map(c => (
                  <option key={c.name} value={c.name}>
                    {c.display_name} ({c.image_count} cards){c.source === 'firebase' ? ' ☁' : ''}
                  </option>
                ))}
              </select>
            ) : (
              <input
                value={selectedCollection}
                onChange={e => setSelectedCollection(e.target.value)}
                placeholder="data/1_full"
                className="mt-1 w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm font-mono text-gray-200 focus:outline-none focus:border-violet-500"
              />
            )}
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <input
              type="checkbox" checked={useCache}
              onChange={e => setUseCache(e.target.checked)}
              className="accent-violet-500"
            />
            Use response cache (faster, cheaper)
          </label>
        </div>

        {error && <p className="text-sm text-red-400 bg-red-900/20 border border-red-500/30 p-3 rounded-lg">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors text-sm"
        >
          {submitting ? '🚀 Starting game…' : '🎮 Start Game & Watch Live'}
        </button>
      </form>
    </div>
  )
}
