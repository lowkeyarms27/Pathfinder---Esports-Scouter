import { useNavigate } from 'react-router-dom'
import { useWatchlist } from '../context/WatchlistContext'
import s from './PlayerCard.module.css'

export default function PlayerCard({ player }) {
  const navigate = useNavigate()
  const { toggle, has } = useWatchlist()
  const watched = has(player.id)

  function handleWatch(e) {
    e.stopPropagation()
    toggle(player)
  }

  return (
    <div className={s.card} onClick={() => navigate(`/player/${player.id}`)}>
      <div className={s.header}>
        <div className={s.avatar}>
          {player.handle.slice(0, 2).toUpperCase()}
        </div>
        <div className={s.info}>
          <div className={s.handle}>{player.handle}</div>
          <div className={s.meta}>{player.nationality} {player.realName} · Age {player.age}</div>
        </div>
        <div className={s.score}>
          <div className={s.scoreNum}>{player.matchScore}</div>
          <div className={s.scoreLabel}>Match</div>
        </div>
      </div>

      <div className={s.tags}>
        <span className={`${s.tag} ${s.tagRole}`}>{player.role}</span>
        <span className={`${s.tag} ${s.tagGame}`}>{player.game}</span>
        {player.trending && <span className={`${s.tag} ${s.tagTrending}`}>Trending</span>}
      </div>

      <div className={s.footer}>
        <span className={s.team}>{player.team}</span>
        <button
          className={`${s.watchBtn} ${watched ? s.watchBtnActive : ''}`}
          onClick={handleWatch}
        >
          {watched ? '★ Watching' : '+ Watch'}
        </button>
      </div>
    </div>
  )
}
