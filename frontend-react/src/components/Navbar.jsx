import { NavLink, useNavigate } from 'react-router-dom'
import { useWatchlist } from '../context/WatchlistContext'
import s from './Navbar.module.css'

export default function Navbar() {
  const { watchlist } = useWatchlist()
  const navigate = useNavigate()

  return (
    <nav className={s.nav}>
      <div className={s.logo}>
        <span className={s.logoAccent}>▲</span> Pathfinder
      </div>
      <div className={s.links}>
        <NavLink to="/" end className={({ isActive }) => `${s.link} ${isActive ? s.linkActive : ''}`}>
          Discover
        </NavLink>
        <NavLink to="/scout" className={({ isActive }) => `${s.link} ${isActive ? s.linkActive : ''}`}>
          Scout
        </NavLink>
        <NavLink to="/watchlist" className={({ isActive }) => `${s.link} ${isActive ? s.linkActive : ''}`}>
          Watchlist
        </NavLink>
      </div>
      <div className={s.right}>
        <button className={s.watchlistBtn} onClick={() => navigate('/watchlist')}>
          Watchlist
          {watchlist.length > 0 && (
            <span className={s.watchlistCount}>{watchlist.length}</span>
          )}
        </button>
        <button className={s.scoutBtn} onClick={() => navigate('/scout')}>
          + Scout Player
        </button>
      </div>
    </nav>
  )
}
