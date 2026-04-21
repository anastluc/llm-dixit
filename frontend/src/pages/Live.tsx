import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

// ─── Types ────────────────────────────────────────────────────────────────────

interface PlayerInfo { name: string; model: string }

interface GameEvent {
  type: string
  // game_config
  players?: PlayerInfo[]
  prompt_style?: string
  prompt_style_name?: string
  clue_prompt?: string
  vote_prompt?: string
  // round events
  round?: number
  storyteller?: string
  clue?: string
  storyteller_card?: string
  player?: string
  card?: string
  voted_card?: string
  score_changes?: Record<string, number>
  current_scores?: Record<string, number>
  storyteller_votes?: number
  // game_over
  winner?: string
  winner_score?: number
  final_scores?: Record<string, number>
  // error
  message?: string
}

interface ScoredRound {
  round: number
  storyteller: string
  clue: string
  storyteller_votes: number
  score_changes: Record<string, number>
  current_scores: Record<string, number>
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function cardUrl(path: string): string {
  const match = path?.match(/data[\\/](.+)/)
  return match ? `/api/images/${match[1]}` : (path ?? '')
}

function shortName(name: string) { return name.split('_')[0] }

// ─── Baseball Scorecard ───────────────────────────────────────────────────────

function BaseballScorecard({ scoredRounds, players }: {
  scoredRounds: ScoredRound[]
  players: string[]
}) {
  if (scoredRounds.length === 0 || players.length === 0) return null
  return (
    <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10 overflow-x-auto">
      <p className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Scorecard</p>
      <table className="text-xs w-full min-w-max border-collapse">
        <thead>
          <tr>
            <th className="text-left py-1.5 pr-5 text-gray-500 font-medium min-w-[120px]">Player</th>
            {scoredRounds.map(r => (
              <th key={r.round} className="text-center py-1.5 px-2 w-9 text-gray-500">{r.round}</th>
            ))}
            <th className="text-center py-1.5 px-3 text-gray-400 font-semibold border-l border-white/10">Σ</th>
          </tr>
        </thead>
        <tbody>
          {players.map(player => {
            const latest = scoredRounds[scoredRounds.length - 1]
            return (
              <tr key={player} className="border-t border-white/5">
                <td className="py-1.5 pr-5 text-gray-300 truncate max-w-[120px]">{shortName(player)}</td>
                {scoredRounds.map(r => {
                  const pts = r.score_changes[player]
                  const isTeller = r.storyteller === player
                  return (
                    <td key={r.round}
                      className={`text-center py-1.5 px-2 rounded
                        ${pts > 0 ? 'text-green-400' : pts < 0 ? 'text-red-400' : 'text-gray-600'}`}>
                      {pts !== undefined ? (pts > 0 ? `+${pts}` : `${pts}`) : '·'}
                      {isTeller && <sup className="text-amber-400 ml-px">★</sup>}
                    </td>
                  )
                })}
                <td className="text-center py-1.5 px-3 font-bold text-white border-l border-white/10">
                  {latest?.current_scores[player] ?? 0}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="text-[10px] text-gray-600 mt-2"><span className="text-amber-400">★</span> storyteller round</p>
    </div>
  )
}

// ─── Commentary Feed ──────────────────────────────────────────────────────────

const EVENT_ICONS: Record<string, string> = {
  game_config:    '🎮',
  round_start:    '🔄',
  clue_generated: '💬',
  card_selected:  '🃏',
  vote_cast:      '🗳️',
  round_scored:   '📊',
  game_over:      '🏆',
  error:          '❌',
}

function EventItem({ ev, playerModels }: { ev: GameEvent; playerModels: Record<string, string> }) {
  const icon = EVENT_ICONS[ev.type] ?? '•'

  if (ev.type === 'game_config') return (
    <div className="flex gap-3 py-2">
      <span className="text-base shrink-0 mt-0.5">{icon}</span>
      <div>
        <p className="text-xs text-gray-400 font-medium">Game starting</p>
        <div className="flex flex-wrap gap-1.5 mt-1">
          {ev.players?.map(p => (
            <span key={p.name} className="text-[10px] bg-white/8 text-gray-400 px-2 py-0.5 rounded-full font-mono">
              {shortName(p.name)} · {p.model.split('/').pop()}
            </span>
          ))}
        </div>
        {ev.prompt_style_name && (
          <p className="text-[10px] text-gray-600 mt-1">Style: {ev.prompt_style_name}</p>
        )}
      </div>
    </div>
  )

  if (ev.type === 'round_start') return (
    <div className="flex gap-3 py-2 border-t border-white/5 mt-1">
      <span className="text-base shrink-0 mt-0.5">{icon}</span>
      <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider mt-1">
        Round {ev.round}
      </p>
    </div>
  )

  if (ev.type === 'clue_generated') return (
    <div className="flex gap-3 py-2">
      <span className="text-base shrink-0 mt-0.5">{icon}</span>
      <div>
        <p className="text-xs text-gray-500">
          <span className="text-gray-300 font-medium">{shortName(ev.storyteller ?? '')}</span>
          {' '}(storyteller)
          {playerModels[ev.storyteller ?? ''] && (
            <span className="text-gray-600 font-mono ml-1">· {playerModels[ev.storyteller ?? ''].split('/').pop()}</span>
          )}
        </p>
        <p className="text-amber-300 font-medium italic mt-1 text-sm">"{ev.clue}"</p>
        {ev.storyteller_card && (
          <img src={cardUrl(ev.storyteller_card)} className="mt-2 h-24 rounded-lg object-cover" alt="storyteller card" />
        )}
      </div>
    </div>
  )

  if (ev.type === 'round_scored') return (
    <div className="flex gap-3 py-2">
      <span className="text-base shrink-0 mt-0.5">{icon}</span>
      <div className="flex-1">
        <p className="text-xs text-gray-500 mb-2">
          Round {ev.round} scored · {ev.storyteller_votes} correct vote(s)
        </p>
        <div className="grid grid-cols-2 gap-1">
          {ev.current_scores && Object.entries(ev.current_scores)
            .sort(([, a], [, b]) => b - a)
            .map(([p, s]) => (
              <div key={p} className="flex justify-between text-xs bg-white/4 px-2 py-1 rounded">
                <span className="text-gray-400 truncate">{shortName(p)}</span>
                <span className="text-white font-mono font-bold ml-2">
                  {s}
                  {ev.score_changes?.[p] ? (
                    <span className="text-green-400 ml-1 font-normal">+{ev.score_changes[p]}</span>
                  ) : null}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  )

  if (ev.type === 'game_over') return (
    <div className="flex gap-3 py-3 mt-2">
      <span className="text-2xl shrink-0">🏆</span>
      <div>
        <p className="text-amber-300 font-bold text-base">Game Over!</p>
        <p className="text-white text-sm mt-0.5">
          Winner: <span className="font-semibold">{ev.winner}</span> ({ev.winner_score} pts)
        </p>
        {ev.final_scores && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {Object.entries(ev.final_scores)
              .sort(([, a], [, b]) => b - a)
              .map(([p, s]) => (
                <span key={p} className={`text-xs px-2 py-0.5 rounded-full font-medium
                  ${p === ev.winner ? 'bg-amber-400/20 text-amber-300' : 'bg-white/8 text-gray-400'}`}>
                  {shortName(p)}: {s}
                </span>
              ))}
          </div>
        )}
      </div>
    </div>
  )

  if (ev.type === 'error') return (
    <div className="flex gap-3 py-2">
      <span className="text-base shrink-0 mt-0.5">{icon}</span>
      <p className="text-xs text-red-400">Error: {ev.message}</p>
    </div>
  )

  // Generic: card_selected, vote_cast
  return (
    <div className="flex gap-3 py-1">
      <span className="text-sm shrink-0 mt-0.5 opacity-50">{icon}</span>
      <p className="text-xs text-gray-600">
        {ev.type === 'card_selected' && `${shortName(ev.player ?? '')} selected a card`}
        {ev.type === 'vote_cast' && `${shortName(ev.player ?? '')} voted`}
      </p>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Live() {
  const { id } = useParams<{ id: string }>()
  const [events, setEvents] = useState<GameEvent[]>([])
  const [status, setStatus] = useState<'connecting' | 'connected' | 'done' | 'error'>('connecting')
  const feedRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${wsProtocol}://${window.location.host}/ws/live/${id}`)
    ws.onopen  = () => setStatus('connected')
    ws.onerror = () => setStatus('error')
    ws.onclose = () => setStatus(s => s === 'connected' ? 'done' : s)
    ws.onmessage = e => {
      if (e.data === 'pong') return
      const ev = JSON.parse(e.data) as GameEvent
      setEvents(prev => [...prev, ev])
      if (ev.type === 'game_over') setStatus('done')
    }
    const ping = setInterval(() => { if (ws.readyState === 1) ws.send('ping') }, 25000)
    return () => { clearInterval(ping); ws.close() }
  }, [id])

  // Auto-scroll feed
  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' })
  }, [events])

  // Derive structured data from event stream
  const gameConfig = events.find(e => e.type === 'game_config')
  const playerModels: Record<string, string> = Object.fromEntries(
    gameConfig?.players?.map(p => [p.name, p.model]) ?? []
  )
  const players = gameConfig?.players?.map(p => p.name) ?? []

  const scoredRounds: ScoredRound[] = events
    .filter(e => e.type === 'round_scored')
    .map(e => {
      const clueEv = [...events]
        .filter(x => x.type === 'clue_generated' && x.round === e.round)
        .pop()
      return {
        round: e.round!,
        storyteller: clueEv?.storyteller ?? '',
        clue: clueEv?.clue ?? '',
        storyteller_votes: e.storyteller_votes ?? 0,
        score_changes: e.score_changes ?? {},
        current_scores: e.current_scores ?? {},
      }
    })

  const latestClue = [...events].reverse().find(e => e.type === 'clue_generated')
  const latestScores = [...events].reverse().find(e => e.type === 'round_scored')?.current_scores

  const statusColor = {
    connecting: 'text-yellow-400',
    connected:  'text-green-400',
    done:       'text-gray-400',
    error:      'text-red-400',
  }
  const statusLabel = {
    connecting: '● Connecting…',
    connected:  '● Live',
    done:       '● Finished',
    error:      '● Connection error',
  }

  return (
    <div className="space-y-5 pb-10">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <Link to="/games" className="text-gray-500 hover:text-white text-sm transition-colors">← Games</Link>
        <h1 className="text-xl font-bold text-white flex-1">🔴 Live: {id}</h1>
        <span className={`text-sm font-medium ${statusColor[status]}`}>{statusLabel[status]}</span>
      </div>

      {/* ── Prompt info (from game_config) ──────────────────────────────────── */}
      {gameConfig?.clue_prompt && (
        <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-1">Storyteller prompt</p>
            <p className="text-xs text-gray-400 leading-relaxed">{gameConfig.clue_prompt}</p>
          </div>
          <div>
            <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-1">Voter prompt</p>
            <p className="text-xs text-gray-400 leading-relaxed">{gameConfig.vote_prompt}</p>
          </div>
        </div>
      )}

      {/* ── Baseball scorecard ───────────────────────────────────────────────── */}
      <BaseballScorecard scoredRounds={scoredRounds} players={players} />

      {/* ── Main layout ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Sidebar: live scoreboard */}
        {latestScores && (
          <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10 h-fit space-y-2">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold">Scoreboard</p>
            {Object.entries(latestScores)
              .sort(([, a], [, b]) => b - a)
              .map(([p, s], i) => (
                <div key={p} className="flex items-center gap-2 py-1">
                  <span className="text-gray-600 text-xs w-4">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-300 truncate">{shortName(p)}</p>
                    {playerModels[p] && (
                      <p className="text-[10px] text-gray-600 font-mono truncate">{playerModels[p].split('/').pop()}</p>
                    )}
                  </div>
                  <span className="text-white font-mono font-bold text-sm">{s}</span>
                </div>
              ))}
          </div>
        )}

        {/* Current round spotlight + event feed */}
        <div className={latestScores ? 'lg:col-span-2' : 'lg:col-span-3'}>

          {/* Current clue banner */}
          {latestClue && (
            <div className="mb-4 p-4 bg-amber-900/15 border border-amber-500/25 rounded-xl">
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">
                Round {latestClue.round} · Current Clue
              </p>
              <p className="text-amber-300 font-medium italic text-xl leading-snug">"{latestClue.clue}"</p>
              <p className="text-xs text-gray-600 mt-1">
                by {latestClue.storyteller}
                {playerModels[latestClue.storyteller ?? ''] && (
                  <span className="font-mono ml-1">· {playerModels[latestClue.storyteller ?? ''].split('/').pop()}</span>
                )}
              </p>
            </div>
          )}

          {/* Commentary feed */}
          <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Commentary</p>
            <div
              ref={feedRef}
              className="space-y-0 max-h-[55vh] overflow-y-auto pr-1 scroll-smooth divide-y divide-white/3"
            >
              {events.length === 0 ? (
                <div className="text-center py-14 text-gray-600">
                  <div className="animate-pulse text-4xl mb-3">🃏</div>
                  <p className="text-sm">Waiting for the game to start…</p>
                  <p className="text-xs mt-1 text-gray-700">Share this URL so others can watch live!</p>
                </div>
              ) : (
                events
                  .filter(ev => ev.type !== 'game_config')
                  .map((ev, i) => (
                    <EventItem key={i} ev={ev} playerModels={playerModels} />
                  ))
              )}
            </div>
          </div>

          <div className="mt-3 p-3 bg-[#1a1d27] rounded-lg border border-white/8">
            <p className="text-xs text-gray-600">
              🔗 <span className="font-mono text-violet-400/80">{window.location.href}</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
