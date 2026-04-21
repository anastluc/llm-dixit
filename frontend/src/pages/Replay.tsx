import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'

// ─── Types ────────────────────────────────────────────────────────────────────

interface CardPlay {
  selected_card: string
  card_scores: Record<string, number>
}

interface Round {
  round: number
  storyteller: string
  clue: string
  storyteller_card: string
  played_cards: Record<string, CardPlay>
  votes: Record<string, CardPlay>
  storyteller_votes: number
  score_changes: Record<string, number>
  current_scores: Record<string, number>
}

interface PlayerCfg { name: string; model: string; provider: string }

interface GameLog {
  game_id: string
  game_configuration: {
    timestamp: string
    prompt_style: string
    prompt_style_name: string
    players: PlayerCfg[]
    max_rounds: number
    score_to_win: number
  }
  rounds: Round[]
}

interface PromptStyleFull {
  id: string
  name: string
  description: string
  clue_prompt: string
  vote_prompt: string
  temperature: number
  max_tokens: number
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SPEED_MS = [5000, 3000, 2000, 1000, 500] // index 0 = slowest

// ─── Helpers ──────────────────────────────────────────────────────────────────

function cardUrl(path: string): string {
  const match = path?.match(/data[\\/](.+)/)
  return match ? `/api/images/${match[1]}` : (path ?? '')
}

function shortName(name: string) {
  return name.split('_')[0]
}

// ─── Components ───────────────────────────────────────────────────────────────

function BaseballScorecard({ rounds, players, currentRound, onSelect }: {
  rounds: Round[]
  players: string[]
  currentRound: number
  onSelect: (idx: number) => void
}) {
  return (
    <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10 overflow-x-auto">
      <p className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Scorecard</p>
      <table className="text-xs w-full min-w-max border-collapse">
        <thead>
          <tr>
            <th className="text-left py-2 pr-5 text-gray-500 font-medium min-w-[130px]">Player</th>
            {rounds.map((r, i) => (
              <th
                key={i}
                onClick={() => onSelect(i)}
                className={`text-center py-2 px-2 w-9 cursor-pointer select-none transition-colors
                  ${i === currentRound
                    ? 'text-violet-200 font-bold bg-violet-700/40 rounded-t'
                    : 'text-gray-500 hover:text-white hover:bg-white/5 rounded-t'}`}
              >
                {r.round}
              </th>
            ))}
            <th className="text-center py-2 px-3 text-gray-400 font-semibold border-l border-white/10">Σ</th>
          </tr>
        </thead>
        <tbody>
          {players.map(player => (
            <tr key={player} className="border-t border-white/5">
              <td className="py-1.5 pr-5 text-gray-300 font-medium truncate max-w-[130px]">
                {shortName(player)}
              </td>
              {rounds.map((r, i) => {
                const pts = r.score_changes[player]
                const isStoryteller = r.storyteller === player
                return (
                  <td
                    key={i}
                    onClick={() => onSelect(i)}
                    title={`Round ${r.round} · ${player}: ${pts > 0 ? '+' : ''}${pts ?? '?'} pts`}
                    className={`text-center py-1.5 px-2 cursor-pointer transition-colors rounded
                      ${i === currentRound ? 'bg-violet-700/25' : 'hover:bg-white/5'}
                      ${pts > 0 ? 'text-green-400' : pts < 0 ? 'text-red-400' : 'text-gray-600'}`}
                  >
                    {pts !== undefined ? (pts > 0 ? `+${pts}` : `${pts}`) : '·'}
                    {isStoryteller && <sup className="text-amber-400 ml-px">★</sup>}
                  </td>
                )
              })}
              <td className="text-center py-1.5 px-3 font-bold text-white border-l border-white/10">
                {rounds[rounds.length - 1]?.current_scores[player] ?? 0}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[10px] text-gray-600 mt-2.5">
        <span className="text-amber-400">★</span> storyteller round &nbsp;·&nbsp; click any column to jump there
      </p>
    </div>
  )
}

function ScoreBar({ scores, players }: { scores: Record<string, number>; players: string[] }) {
  const max = Math.max(...Object.values(scores), 1)
  return (
    <div className="space-y-2.5">
      {[...players].sort((a, b) => (scores[b] ?? 0) - (scores[a] ?? 0)).map(p => (
        <div key={p} className="flex items-center gap-3 text-xs">
          <span className="w-28 truncate text-gray-400 text-right shrink-0">{shortName(p)}</span>
          <div className="flex-1 h-2.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-violet-600 to-violet-400 rounded-full transition-all duration-700"
              style={{ width: `${((scores[p] ?? 0) / max) * 100}%` }}
            />
          </div>
          <span className="w-8 text-right text-white font-mono font-bold shrink-0">{scores[p] ?? 0}</span>
        </div>
      ))}
    </div>
  )
}

function CardTile({ path, label, highlight, votes, voterScores }: {
  path: string
  label: string
  highlight?: boolean
  votes?: string[]
  voterScores?: Record<string, number>
}) {
  return (
    <div className={`rounded-xl overflow-hidden border-2 transition-all
      ${highlight
        ? 'border-amber-400 shadow-lg shadow-amber-400/20'
        : 'border-white/10 hover:border-white/25'}`}
    >
      <div className="relative">
        <img
          src={cardUrl(path)}
          alt={label}
          className="w-full h-36 object-cover"
          onError={e => {
            (e.target as HTMLImageElement).src =
              'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="144"><rect width="200" height="144" fill="%23333"/><text x="100" y="77" text-anchor="middle" fill="%23666" font-size="11">No image</text></svg>'
          }}
        />
        {highlight && (
          <span className="absolute top-1.5 right-1.5 bg-amber-400 text-black text-[8px] font-extrabold px-1.5 py-0.5 rounded-full tracking-wide">
            STORY
          </span>
        )}
      </div>
      <div className="p-2.5 bg-[#1a1d27] space-y-1.5">
        <p className="text-xs text-gray-300 font-medium truncate">{shortName(label)}</p>

        {/* Who voted for this card */}
        {votes && votes.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {votes.map(v => (
              <span key={v} className="text-[10px] bg-violet-900/60 text-violet-300 px-1.5 py-0.5 rounded-full">
                🗳 {shortName(v)}
              </span>
            ))}
          </div>
        )}

        {/* Scores each voter assigned to this card */}
        {voterScores && Object.keys(voterScores).length > 0 && (
          <div className="grid grid-cols-2 gap-0.5 mt-1">
            {Object.entries(voterScores)
              .sort(([, a], [, b]) => b - a)
              .map(([voter, score]) => (
                <div key={voter} className="flex justify-between text-[10px] bg-white/5 px-1.5 py-0.5 rounded">
                  <span className="text-gray-500 truncate">{shortName(voter)}</span>
                  <span className={`font-mono font-bold ml-1
                    ${score >= 7 ? 'text-green-400' : score >= 4 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {score}
                  </span>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  )
}

function RoundTimeline({ rounds, players, currentRound, onSelect }: {
  rounds: Round[]
  players: string[]
  currentRound: number
  onSelect: (idx: number) => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current?.querySelector(`[data-ri="${currentRound}"]`) as HTMLElement | null
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [currentRound])

  return (
    <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10">
      <p className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Game Timeline</p>
      <div ref={ref} className="space-y-1.5 max-h-80 overflow-y-auto pr-1 scroll-smooth">
        {rounds.map((r, i) => {
          const isCurrent = i === currentRound
          const topScorer = Object.entries(r.score_changes).sort(([, a], [, b]) => b - a)[0]
          return (
            <button
              key={i}
              data-ri={i}
              onClick={() => onSelect(i)}
              className={`w-full text-left p-3 rounded-lg transition-all border
                ${isCurrent
                  ? 'bg-violet-900/25 border-violet-500/40'
                  : 'border-transparent hover:bg-white/4 hover:border-white/8'}`}
            >
              <div className="flex items-start gap-2.5">
                {/* Round badge */}
                <span className={`shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded font-bold mt-0.5
                  ${isCurrent ? 'bg-violet-600 text-white' : 'bg-white/10 text-gray-500'}`}>
                  R{r.round}
                </span>

                <div className="flex-1 min-w-0">
                  {/* Clue */}
                  <p className="text-xs text-amber-300 italic truncate font-medium">"{r.clue}"</p>
                  {/* Meta */}
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    Storyteller: <span className="text-gray-400">{shortName(r.storyteller)}</span>
                    &nbsp;·&nbsp;
                    {r.storyteller_votes}/{players.length - 1} guessed correctly
                  </p>
                  {/* Score pills */}
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {Object.entries(r.score_changes)
                      .sort(([, a], [, b]) => b - a)
                      .map(([p, pts]) => (
                        <span key={p} className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium
                          ${pts > 0
                            ? 'bg-green-900/40 text-green-400'
                            : pts === 0
                              ? 'bg-white/5 text-gray-600'
                              : 'bg-red-900/30 text-red-400'}`}>
                          {shortName(p)} {pts > 0 ? `+${pts}` : `${pts}`}
                        </span>
                      ))}
                  </div>
                </div>

                {/* Cumulative leader score */}
                {topScorer && topScorer[1] > 0 && (
                  <span className="shrink-0 text-[10px] text-green-400 font-mono font-bold mt-0.5">
                    +{topScorer[1]}
                  </span>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Replay() {
  const { id } = useParams<{ id: string }>()
  const [log, setLog] = useState<GameLog | null>(null)
  const [styles, setStyles] = useState<PromptStyleFull[]>([])
  const [roundIdx, setRoundIdx] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(3)          // 1 = slowest … 5 = fastest
  const [showPrompts, setShowPrompts] = useState(false)

  useEffect(() => {
    fetch(`/api/games/${id}`).then(r => r.json()).then(setLog)
    fetch('/api/prompt-styles').then(r => r.json()).then(setStyles)
  }, [id])

  const totalRounds = log?.rounds.length ?? 1
  const round: Round | undefined = log?.rounds[roundIdx]
  const players = log?.game_configuration.players.map(p => p.name) ?? []
  const playerModels = Object.fromEntries(
    log?.game_configuration.players.map(p => [p.name, p.model]) ?? []
  )
  const currentStyle = styles.find(s => s.id === log?.game_configuration.prompt_style)

  const next = useCallback(() => {
    setRoundIdx(i => Math.min(i + 1, (log?.rounds.length ?? 1) - 1))
  }, [log])
  const prev = useCallback(() => setRoundIdx(i => Math.max(i - 1, 0)), [])

  useEffect(() => {
    if (!playing) return
    const t = setInterval(next, SPEED_MS[speed - 1])
    return () => clearInterval(t)
  }, [playing, next, speed])

  // Stop auto-play at last round
  useEffect(() => {
    if (log && roundIdx >= log.rounds.length - 1) setPlaying(false)
  }, [roundIdx, log])

  if (!log || !round) return (
    <div className="text-center py-24 text-gray-500 animate-pulse">Loading replay…</div>
  )

  // Build vote map: card_path → voters
  const voteMap: Record<string, string[]> = {}
  for (const [voter, v] of Object.entries(round.votes)) {
    voteMap[v.selected_card] = [...(voteMap[v.selected_card] ?? []), voter]
  }

  // Build per-card voter scores: card_path → { voter: score }
  const cardVoterScores: Record<string, Record<string, number>> = {}
  for (const [voter, voteData] of Object.entries(round.votes)) {
    for (const [cardPath, score] of Object.entries(voteData.card_scores)) {
      if (!cardVoterScores[cardPath]) cardVoterScores[cardPath] = {}
      cardVoterScores[cardPath][voter] = score
    }
  }

  // All played cards: storyteller first, then others
  const allPlayed = [
    { player: round.storyteller, card: round.storyteller_card },
    ...Object.entries(round.played_cards).map(([player, p]) => ({ player, card: p.selected_card })),
  ]

  return (
    <div className="space-y-5 pb-12">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        <Link to="/games" className="text-gray-500 hover:text-white text-sm transition-colors">← Games</Link>
        <h1 className="text-xl font-bold text-white flex-1">🎬 Replay: {id}</h1>
        <span className="text-xs text-gray-600 hidden sm:block">
          {log.game_configuration.prompt_style_name} &nbsp;·&nbsp; {log.rounds.length} rounds
        </span>
        <Link
          to={`/live/${id}`}
          className="text-xs px-3 py-1.5 rounded-lg bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600/30 transition-colors"
        >
          🔴 Live View
        </Link>
      </div>

      {/* ── Baseball Scorecard ──────────────────────────────────────────────── */}
      <BaseballScorecard
        rounds={log.rounds}
        players={players}
        currentRound={roundIdx}
        onSelect={i => { setRoundIdx(i); setPlaying(false) }}
      />

      {/* ── Controls ────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 p-4 bg-[#1a1d27] rounded-xl border border-white/10">
        <button
          onClick={prev}
          disabled={roundIdx === 0}
          className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 disabled:opacity-30 text-sm transition-colors"
        >← Prev</button>

        <div className="flex-1 min-w-[80px] relative h-2 bg-white/10 rounded-full">
          <input
            type="range" min={0} max={totalRounds - 1} value={roundIdx}
            onChange={e => { setRoundIdx(+e.target.value); setPlaying(false) }}
            className="absolute inset-0 w-full opacity-0 cursor-pointer h-full"
          />
          <div
            className="h-full bg-violet-500 rounded-full pointer-events-none transition-all"
            style={{ width: `${(roundIdx / Math.max(totalRounds - 1, 1)) * 100}%` }}
          />
        </div>

        <span className="text-sm text-gray-400 font-mono whitespace-nowrap">
          R {roundIdx + 1} / {totalRounds}
        </span>

        <button
          onClick={next}
          disabled={roundIdx === totalRounds - 1}
          className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 disabled:opacity-30 text-sm transition-colors"
        >Next →</button>

        <button
          onClick={() => setPlaying(p => !p)}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors
            ${playing ? 'bg-red-600 hover:bg-red-500 text-white' : 'bg-violet-600 hover:bg-violet-500 text-white'}`}
        >
          {playing ? '⏸ Pause' : '▶ Play'}
        </button>

        {/* Speed slider */}
        <div className="flex items-center gap-1.5 text-xs text-gray-500" title="Playback speed">
          <span>🐢</span>
          <input
            type="range" min={1} max={5} value={speed}
            onChange={e => setSpeed(+e.target.value)}
            className="w-20 accent-violet-500 cursor-pointer"
          />
          <span>🐇</span>
          <span className="text-gray-600 font-mono">{SPEED_MS[speed - 1] / 1000}s</span>
        </div>
      </div>

      {/* ── Main grid ───────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Left column */}
        <div className="space-y-4">

          {/* Prompt style panel */}
          {currentStyle && (
            <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10">
              <button
                onClick={() => setShowPrompts(p => !p)}
                className="flex items-center justify-between w-full text-left group"
              >
                <div>
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider">Prompt Style</p>
                  <p className="text-sm font-semibold text-violet-300 mt-0.5">{currentStyle.name}</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">{currentStyle.description}</p>
                </div>
                <span className="text-gray-600 group-hover:text-gray-400 text-xs ml-3 shrink-0">
                  {showPrompts ? '▲' : '▼'} prompts
                </span>
              </button>
              {showPrompts && (
                <div className="mt-3 space-y-3 border-t border-white/8 pt-3">
                  <div>
                    <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-1">Storyteller sees</p>
                    <p className="text-xs text-gray-400 leading-relaxed bg-white/3 p-2 rounded-lg">
                      {currentStyle.clue_prompt}
                    </p>
                  </div>
                  <div>
                    <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-1">Voter sees</p>
                    <p className="text-xs text-gray-400 leading-relaxed bg-white/3 p-2 rounded-lg">
                      {currentStyle.vote_prompt}
                    </p>
                  </div>
                  <p className="text-[10px] text-gray-600">
                    temp {currentStyle.temperature} · max {currentStyle.max_tokens} tokens
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Storyteller + Clue */}
          <div className="p-4 bg-[#1a1d27] rounded-xl border border-amber-400/20">
            <p className="text-[10px] text-gray-600 uppercase tracking-wider">Round {round.round} · Storyteller</p>
            <p className="font-semibold text-white mt-1">{round.storyteller}</p>
            {playerModels[round.storyteller] && (
              <p className="text-[10px] text-gray-600 font-mono mt-0.5 truncate">
                {playerModels[round.storyteller]}
              </p>
            )}
            <div className="mt-3 pt-3 border-t border-white/8">
              <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5">Clue</p>
              <p className="text-amber-300 font-medium italic text-base leading-snug">"{round.clue}"</p>
            </div>
          </div>

          {/* Storyteller's card */}
          <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10">
            <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2">Storyteller's Card</p>
            <img
              src={cardUrl(round.storyteller_card)}
              alt="storyteller card"
              className="w-full rounded-lg object-cover"
              onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          </div>

          {/* Votes + score delta */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10 text-center">
              <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Correct Votes</p>
              <p className="text-3xl font-bold text-white">{round.storyteller_votes}</p>
              <p className="text-xs text-gray-600">of {players.length - 1}</p>
            </div>
            <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10">
              <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2">Score Δ</p>
              <div className="space-y-1">
                {Object.entries(round.score_changes)
                  .sort(([, a], [, b]) => b - a)
                  .map(([p, d]) => (
                    <div key={p} className="flex justify-between text-xs">
                      <span className="text-gray-400 truncate">{shortName(p)}</span>
                      <span className={`font-mono font-bold ml-2
                        ${d > 0 ? 'text-green-400' : d < 0 ? 'text-red-400' : 'text-gray-600'}`}>
                        {d > 0 ? `+${d}` : d}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="lg:col-span-2 space-y-5">
          {/* Cards in play */}
          <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10">
            <p className="text-[10px] text-gray-600 uppercase tracking-widest font-semibold mb-3">
              Cards in Play &nbsp;·&nbsp; voters see these anonymously
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {allPlayed.map(({ player, card }) => (
                <CardTile
                  key={card}
                  path={card}
                  label={player}
                  highlight={card === round.storyteller_card}
                  votes={voteMap[card]}
                  voterScores={cardVoterScores[card]}
                />
              ))}
            </div>
          </div>

          {/* Score bar */}
          <div className="p-4 bg-[#1a1d27] rounded-xl border border-white/10">
            <p className="text-[10px] text-gray-600 uppercase tracking-widest font-semibold mb-3">
              Cumulative scores after round {round.round}
            </p>
            <ScoreBar scores={round.current_scores} players={players} />
          </div>
        </div>
      </div>

      {/* ── Timeline ────────────────────────────────────────────────────────── */}
      <RoundTimeline
        rounds={log.rounds}
        players={players}
        currentRound={roundIdx}
        onSelect={i => { setRoundIdx(i); setPlaying(false) }}
      />
    </div>
  )
}
