import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface GameSummary {
  game_id: string
  timestamp: string
  prompt_style: string
  prompt_style_name: string
  players: string[]
  models: string[]
  rounds_played: number
  max_rounds: number
  winner: string | null
  final_scores: Record<string, number>
}

function formatTimestamp(ts: string): string {
  if (!ts || ts.length < 15) return ts
  // Format: YYYYMMdd_HHmmss
  const y = ts.slice(0, 4), mo = ts.slice(4, 6), d = ts.slice(6, 8)
  const h = ts.slice(9, 11), mi = ts.slice(11, 13), s = ts.slice(13, 15)
  return `${y}-${mo}-${d} ${h}:${mi}:${s}`
}

const STYLE_BADGE: Record<string, string> = {
  creative: 'bg-violet-900/50 text-violet-300',
  deceptive: 'bg-red-900/50 text-red-300',
  minimalist: 'bg-gray-700 text-gray-300',
  narrative: 'bg-amber-900/50 text-amber-300',
}

export default function Games() {
  const [games, setGames] = useState<GameSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)

  function loadGames() {
    fetch('/api/games')
      .then(r => r.json())
      .then(d => { setGames(d); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { loadGames() }, [])

  async function resetDatabase() {
    if (!confirm('Delete ALL games from the database? This cannot be undone.')) return
    setResetting(true)
    await fetch('/api/games', { method: 'DELETE' })
    setGames([])
    setResetting(false)
  }

  if (loading) return <div className="text-center py-20 text-gray-400">Loading games…</div>
  if (!games.length) return (
    <div className="text-center py-20 text-gray-400">
      <p className="text-4xl mb-4">🎴</p>
      <p>No games recorded yet. <Link to="/new" className="text-violet-400 hover:underline">Start one!</Link></p>
    </div>
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">🎴 Game History</h1>
        <div className="flex gap-2">
          <button
            onClick={resetDatabase}
            disabled={resetting}
            className="px-3 py-2 bg-red-900/40 hover:bg-red-800/60 disabled:opacity-40 text-red-400 text-sm rounded-lg font-medium transition-colors border border-red-500/20"
          >
            {resetting ? 'Deleting…' : 'Reset DB'}
          </button>
          <Link
            to="/new"
            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm rounded-lg font-medium transition-colors"
          >
            + New Game
          </Link>
        </div>
      </div>
      <div className="space-y-3">
        {games.map(g => (
          <Link
            key={g.game_id}
            to={`/games/${g.game_id}`}
            className="block p-4 rounded-xl border border-white/10 bg-[#1a1d27] hover:border-violet-500/50 hover:bg-[#1e2030] transition-all"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className="text-xs text-gray-500 font-mono">{formatTimestamp(g.timestamp)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STYLE_BADGE[g.prompt_style] ?? 'bg-gray-700 text-gray-300'}`}>
                    {g.prompt_style_name || g.prompt_style}
                  </span>
                  <span className="text-xs text-gray-500">{g.rounds_played} rounds</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {g.models.map((m, i) => (
                    <span
                      key={i}
                      className={`text-xs px-2 py-0.5 rounded font-mono ${g.players[i] === g.winner ? 'bg-amber-900/60 text-amber-300 font-semibold' : 'bg-white/5 text-gray-400'}`}
                    >
                      {m.split('/').pop()} {g.players[i] === g.winner ? '🏆' : ''}
                    </span>
                  ))}
                </div>
              </div>
              <div className="text-right shrink-0">
                {g.winner && (
                  <div className="text-amber-400 font-semibold text-sm">
                    {g.final_scores[g.winner]} pts
                  </div>
                )}
                <div className="text-xs text-gray-500 mt-0.5">→ replay</div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
