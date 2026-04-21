import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

interface CardMeta {
  filename: string
  url: string
}

interface Collection {
  name: string
  display_name: string
  source: string
  image_count: number
  cards: CardMeta[]
}

interface StorytellerRound {
  game_id: string
  round: number
  model: string
  clue: string
  votes_for: number
  num_voters: number
  outcome: 'success' | 'fail' | 'unknown'
}

interface DecoyRound {
  game_id: string
  round: number
  storyteller_clue: string
  was_voted_for: boolean
}

interface CardStats {
  filename: string
  collection: string
  total_appearances: number
  as_storyteller: {
    count: number
    success_rate: number | null
    rounds: StorytellerRound[]
  }
  as_decoy: {
    count: number
    deceived_count: number
    rounds: DecoyRound[]
  }
}

function outcomeColor(outcome: string) {
  if (outcome === 'success') return 'text-green-400'
  if (outcome === 'fail') return 'text-red-400'
  return 'text-gray-500'
}

function StatsPanel({ stats, onClose }: { stats: CardStats; onClose: () => void }) {
  const { as_storyteller: st, as_decoy: dec } = stats
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={onClose}>
      <div
        className="bg-[#1a1d27] border border-white/10 rounded-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto p-5 space-y-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <p className="font-semibold text-white font-mono text-sm">{stats.filename}</p>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>

        {/* Summary row */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Total appearances', value: stats.total_appearances },
            { label: 'As storyteller', value: st.count },
            {
              label: 'Success rate',
              value: st.success_rate !== null ? `${Math.round(st.success_rate * 100)}%` : '—',
            },
          ].map(({ label, value }) => (
            <div key={label} className="p-2 bg-white/5 rounded-lg text-center">
              <p className="text-lg font-bold text-white">{value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'As decoy', value: dec.count },
            { label: 'Deceived voters', value: dec.deceived_count },
          ].map(({ label, value }) => (
            <div key={label} className="p-2 bg-white/5 rounded-lg text-center">
              <p className="text-lg font-bold text-white">{value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>

        {/* Storyteller rounds */}
        {st.rounds.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Clues given</p>
            {st.rounds.map((r, i) => (
              <div key={i} className="p-3 bg-white/5 rounded-lg space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-gray-500">
                    <Link to={`/games/${r.game_id}`} className="hover:text-violet-400">
                      {r.game_id}
                    </Link>
                    {' '}· Round {r.round}
                  </span>
                  <span className={`text-xs font-medium ${outcomeColor(r.outcome)}`}>
                    {r.outcome === 'success' ? '✓ success' : r.outcome === 'fail' ? '✗ fail' : '?'}
                  </span>
                </div>
                <p className="text-sm text-white italic">"{r.clue}"</p>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span className="font-mono">{r.model}</span>
                  <span>{r.votes_for}/{r.num_voters} voted correctly</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Decoy rounds */}
        {dec.rounds.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">As decoy</p>
            {dec.rounds.map((r, i) => (
              <div key={i} className="p-3 bg-white/5 rounded-lg space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-gray-500">
                    <Link to={`/games/${r.game_id}`} className="hover:text-violet-400">
                      {r.game_id}
                    </Link>
                    {' '}· Round {r.round}
                  </span>
                  <span className={`text-xs font-medium ${r.was_voted_for ? 'text-amber-400' : 'text-gray-600'}`}>
                    {r.was_voted_for ? '🎭 deceived' : 'not chosen'}
                  </span>
                </div>
                <p className="text-xs text-gray-400 italic">Clue: "{r.storyteller_clue}"</p>
              </div>
            ))}
          </div>
        )}

        {stats.total_appearances === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            This card hasn't appeared in any completed game yet.
          </p>
        )}
      </div>
    </div>
  )
}

export default function CardExplorer() {
  const { name } = useParams<{ name: string }>()
  const [collection, setCollection] = useState<Collection | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedCard, setSelectedCard] = useState<CardMeta | null>(null)
  const [stats, setStats] = useState<CardStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [filter, setFilter] = useState<'all' | 'used' | 'unused'>('all')
  const [usedSet, setUsedSet] = useState<Set<string>>(new Set())
  const [usedLoaded, setUsedLoaded] = useState(false)

  useEffect(() => {
    if (!name) return
    setLoading(true)
    fetch(`/api/collections/${encodeURIComponent(name)}`)
      .then(r => {
        if (!r.ok) throw new Error('Not found')
        return r.json()
      })
      .then(setCollection)
      .catch(() => setError('Collection not found'))
      .finally(() => setLoading(false))
  }, [name])

  // Pre-fetch which cards have appeared in games
  useEffect(() => {
    if (!collection || usedLoaded) return
    // Fetch stats for all cards in parallel (but limit concurrency)
    const cards = collection.cards || []
    if (cards.length === 0) { setUsedLoaded(true); return }

    // Quick batch: just check total_appearances > 0
    let completed = 0
    const used = new Set<string>()
    const CONCURRENCY = 8

    async function fetchBatch(batch: CardMeta[]) {
      await Promise.all(batch.map(async card => {
        try {
          const res = await fetch(
            `/api/collections/${encodeURIComponent(name!)}/cards/${encodeURIComponent(card.filename)}/stats`
          )
          const data: CardStats = await res.json()
          if (data.total_appearances > 0) used.add(card.filename)
        } catch { /* ignore */ }
        completed++
        if (completed === cards.length) {
          setUsedSet(new Set(used))
          setUsedLoaded(true)
        }
      }))
    }

    for (let i = 0; i < cards.length; i += CONCURRENCY) {
      fetchBatch(cards.slice(i, i + CONCURRENCY))
    }
  }, [collection, name])

  async function openCard(card: CardMeta) {
    setSelectedCard(card)
    setStats(null)
    setStatsLoading(true)
    try {
      const res = await fetch(
        `/api/collections/${encodeURIComponent(name!)}/cards/${encodeURIComponent(card.filename)}/stats`
      )
      setStats(await res.json())
    } catch {
      setStats(null)
    } finally {
      setStatsLoading(false)
    }
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading…</p>
  if (error || !collection) return (
    <div className="text-center py-12 text-gray-500">
      <p className="text-lg">Collection not found</p>
      <Link to="/collections" className="text-violet-400 text-sm mt-2 inline-block">← Back to collections</Link>
    </div>
  )

  const cards = collection.cards || []
  const filteredCards = cards.filter(c => {
    if (filter === 'used') return usedSet.has(c.filename)
    if (filter === 'unused') return !usedSet.has(c.filename)
    return true
  })

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <Link to="/collections" className="hover:text-violet-400">Collections</Link>
            <span>›</span>
            <span>{collection.display_name}</span>
          </div>
          <h1 className="text-2xl font-bold text-white">{collection.display_name}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {collection.image_count} cards ·{' '}
            <span className={collection.source === 'firebase' ? 'text-amber-400' : 'text-blue-400'}>
              {collection.source === 'firebase' ? '☁️ Firebase' : '💻 Local'}
            </span>
            {usedLoaded && ` · ${usedSet.size} used in games`}
          </p>
        </div>
        <Link
          to="/new"
          className="px-4 py-2 text-sm font-medium rounded-lg bg-violet-600 hover:bg-violet-500 text-white transition-colors"
        >
          🎮 New Game with this collection
        </Link>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {(['all', 'used', 'unused'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all capitalize ${
              filter === f
                ? 'border-violet-500 bg-violet-900/30 text-white'
                : 'border-white/10 text-gray-400 hover:border-white/30'
            }`}
          >
            {f} {f !== 'all' && usedLoaded && (
              <span className="ml-1 text-gray-600">
                ({f === 'used' ? usedSet.size : cards.length - usedSet.size})
              </span>
            )}
          </button>
        ))}
        {!usedLoaded && filter !== 'all' && (
          <span className="text-xs text-gray-600 self-center ml-1">Loading usage data…</span>
        )}
      </div>

      {/* Card grid */}
      <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
        {filteredCards.map(card => {
          const used = usedSet.has(card.filename)
          return (
            <button
              key={card.filename}
              onClick={() => openCard(card)}
              className="relative group rounded-lg overflow-hidden aspect-square focus:outline-none focus:ring-2 focus:ring-violet-500"
              title={card.filename}
            >
              <img
                src={card.url}
                alt={card.filename}
                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                loading="lazy"
              />
              {/* Usage indicator dot */}
              {usedLoaded && (
                <span className={`absolute top-1 right-1 w-2 h-2 rounded-full ${
                  used ? 'bg-green-400' : 'bg-gray-600'
                }`} />
              )}
              {/* Hover overlay */}
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-1">
                <p className="text-white text-xs font-mono truncate w-full text-center leading-tight">
                  {card.filename}
                </p>
              </div>
            </button>
          )
        })}
      </div>

      {filteredCards.length === 0 && (
        <p className="text-center text-gray-500 py-12">No cards match this filter.</p>
      )}

      {/* Stats panel modal */}
      {selectedCard && (
        statsLoading ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
            <p className="text-gray-400">Loading stats…</p>
          </div>
        ) : stats ? (
          <StatsPanel stats={stats} onClose={() => { setSelectedCard(null); setStats(null) }} />
        ) : null
      )}
    </div>
  )
}
