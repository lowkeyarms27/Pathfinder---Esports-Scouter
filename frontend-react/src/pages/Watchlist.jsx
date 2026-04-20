import { useNavigate } from 'react-router-dom'
import { useWatchlist } from '../context/WatchlistContext'
import PlayerCard from '../components/PlayerCard'
import s from './Watchlist.module.css'

export default function Watchlist() {
  const { watchlist } = useWatchlist()
  const navigate = useNavigate()

  return (
    <div className={s.page}>
      <div className={s.header}>
        <div className={s.eyebrow}>Watchlist</div>
        <div className={s.title}>Your Tracked Players</div>
        {watchlist.length > 0 && (
          <div className={s.count}>{watchlist.length} player{watchlist.length !== 1 ? 's' : ''} tracked</div>
        )}
      </div>

      {watchlist.length === 0 ? (
        <div className={s.empty}>
          <div className={s.emptyIcon}>☆</div>
          <div className={s.emptyTitle}>No players on your watchlist yet</div>
          <div className={s.emptySub}>Browse the Discover page and click "+ Watch" on any player.</div>
          <button className={s.discoverBtn} onClick={() => navigate('/')}>
            Discover Players
          </button>
        </div>
      ) : (
        <div className={s.grid}>
          {watchlist.map(p => <PlayerCard key={p.id} player={p} />)}
        </div>
      )}
    </div>
  )
}
