import { useEffect, useState } from 'react'

interface ModelStats {
  model: string
  provider: string
  games_played: number
  wins: number
  win_rate: number
  avg_score: number
  avg_score_per_round: number
  storyteller_success_rate: number
}

type SortKey = keyof ModelStats

const MEDAL = ['🥇', '🥈', '🥉']

export default function Leaderboard() {
  const [data, setData] = useState<ModelStats[]>([])
  const [loading, setLoading] = useState(true)
  const [sort, setSort] = useState<SortKey>('win_rate')
  const [asc, setAsc] = useState(false)

  useEffect(() => {
    fetch('/api/leaderboard')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const sorted = [...data].sort((a, b) => {
    const va = a[sort] as number
    const vb = b[sort] as number
    return asc ? va - vb : vb - va
  })

  function toggleSort(key: SortKey) {
    if (sort === key) setAsc(a => !a)
    else { setSort(key); setAsc(false) }
  }

  const Th = ({ label, k }: { label: string; k: SortKey }) => (
    <th
      onClick={() => toggleSort(k)}
      className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white select-none"
    >
      {label} {sort === k ? (asc ? '↑' : '↓') : ''}
    </th>
  )

  if (loading) return <div className="text-center py-20 text-gray-400">Loading leaderboard…</div>
  if (!data.length) return (
    <div className="text-center py-20 text-gray-400">
      <p className="text-4xl mb-4">📭</p>
      <p>No games played yet. <a href="/new" className="text-violet-400 hover:underline">Start a game!</a></p>
    </div>
  )

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">🏆 Model Leaderboard</h1>
      <div className="rounded-xl overflow-hidden border border-white/10 bg-[#1a1d27]">
        <table className="w-full text-sm">
          <thead className="bg-white/5">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">#</th>
              <Th label="Model" k="model" />
              <Th label="Provider" k="provider" />
              <Th label="Games" k="games_played" />
              <Th label="Wins" k="wins" />
              <Th label="Win Rate" k="win_rate" />
              <Th label="Avg Score" k="avg_score" />
              <Th label="Score/Round" k="avg_score_per_round" />
              <Th label="Storyteller %" k="storyteller_success_rate" />
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {sorted.map((row, i) => (
              <tr key={row.model} className="hover:bg-white/5 transition-colors">
                <td className="px-4 py-3 text-gray-500">{MEDAL[i] ?? i + 1}</td>
                <td className="px-4 py-3 font-mono text-violet-300 font-medium">{row.model}</td>
                <td className="px-4 py-3 text-gray-400">{row.provider}</td>
                <td className="px-4 py-3 text-center">{row.games_played}</td>
                <td className="px-4 py-3 text-center">{row.wins}</td>
                <td className="px-4 py-3 text-center">
                  <WinRateBar value={row.win_rate} />
                </td>
                <td className="px-4 py-3 text-center">{row.avg_score.toFixed(1)}</td>
                <td className="px-4 py-3 text-center">{row.avg_score_per_round.toFixed(2)}</td>
                <td className="px-4 py-3 text-center">
                  <span className={row.storyteller_success_rate >= 0.5 ? 'text-green-400' : 'text-amber-400'}>
                    {(row.storyteller_success_rate * 100).toFixed(0)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-gray-500 text-right">
        {data.length} models · click column headers to sort
      </p>
    </div>
  )
}

function WinRateBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full bg-violet-500 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs w-8 text-right">{pct}%</span>
    </div>
  )
}
