import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Leaderboard from './pages/Leaderboard'
import Games from './pages/Games'
import Replay from './pages/Replay'
import Live from './pages/Live'
import NewGame from './pages/NewGame'
import Collections from './pages/Collections'
import CardExplorer from './pages/CardExplorer'

function Nav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-violet-600 text-white'
        : 'text-gray-400 hover:text-white hover:bg-white/10'
    }`

  return (
    <nav className="border-b border-white/10 bg-[#1a1d27]">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-2">
        <span className="text-violet-400 font-bold text-lg mr-4">🃏 Dixit Arena</span>
        <NavLink to="/" end className={linkClass}>Leaderboard</NavLink>
        <NavLink to="/games" className={linkClass}>Games</NavLink>
        <NavLink to="/new" className={linkClass}>New Game</NavLink>
        <NavLink to="/collections" className={linkClass}>Collections</NavLink>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Routes>
          <Route path="/" element={<Leaderboard />} />
          <Route path="/games" element={<Games />} />
          <Route path="/games/:id" element={<Replay />} />
          <Route path="/live/:id" element={<Live />} />
          <Route path="/new" element={<NewGame />} />
          <Route path="/collections" element={<Collections />} />
          <Route path="/collections/:name" element={<CardExplorer />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
