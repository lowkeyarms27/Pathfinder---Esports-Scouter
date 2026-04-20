import { useState, useMemo } from 'react'
import { PLAYERS, GAMES, ROLES, TRENDING, RECENTLY_SCOUTED } from '../data/mockData'
import PlayerCard from '../components/PlayerCard'
import s from './Discover.module.css'

export default function Discover() {
  const [query, setQuery]   = useState('')
  const [game,  setGame]    = useState('All')
  const [role,  setRole]    = useState('All')

  const filtered = useMemo(() => {
    return PLAYERS.filter(p => {
      const q = query.toLowerCase()
      const matchQ = !q || p.handle.toLowerCase().includes(q) || p.team.toLowerCase().includes(q) || p.realName.toLowerCase().includes(q)
      const matchG = game === 'All' || p.game === game
      const matchR = role === 'All' || p.role === role
      return matchQ && matchG && matchR
    })
  }, [query, game, role])

  const isFiltered = query || game !== 'All' || role !== 'All'

  return (
    <div className={s.page}>
      <div className={s.hero}>
        <div className={s.heroEyebrow}>Esports Talent Intelligence</div>
        <h1 className={s.heroTitle}>
          Find your next<br /><span className={s.heroAccent}>pro talent</span>
        </h1>
        <p className={s.heroSub}>
          Stylistic profiling and pro-matching for the competitive scouting era.
        </p>
        <div className={s.searchWrap}>
          <span className={s.searchIcon}>⌕</span>
          <input
            className={s.search}
            placeholder="Search by handle, team, or name…"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className={s.filters}>
        <span className={s.filterLabel}>Game</span>
        {GAMES.map(g => (
          <button key={g} className={`${s.pill} ${game === g ? s.pillActive : ''}`} onClick={() => setGame(g)}>
            {g}
          </button>
        ))}
        <span className={s.filterLabel} style={{ marginLeft: 8 }}>Role</span>
        {ROLES.slice(0, 6).map(r => (
          <button key={r} className={`${s.pill} ${role === r ? s.pillActive : ''}`} onClick={() => setRole(r)}>
            {r}
          </button>
        ))}
      </div>

      {isFiltered ? (
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <span className={s.sectionTitle}>Results</span>
            <span className={s.sectionCount}>{filtered.length} players</span>
          </div>
          {filtered.length > 0 ? (
            <div className={s.grid}>
              {filtered.map(p => <PlayerCard key={p.id} player={p} />)}
            </div>
          ) : (
            <div className={s.empty}>No players match your filters.</div>
          )}
        </div>
      ) : (
        <>
          {TRENDING.length > 0 && (
            <div className={s.section}>
              <div className={s.sectionHeader}>
                <span className={s.sectionTitle}>Trending</span>
                <span className={s.sectionCount}>{TRENDING.length} players</span>
              </div>
              <div className={s.grid}>
                {TRENDING.map(p => <PlayerCard key={p.id} player={p} />)}
              </div>
            </div>
          )}
          {RECENTLY_SCOUTED.length > 0 && (
            <div className={s.section}>
              <div className={s.sectionHeader}>
                <span className={s.sectionTitle}>Recently Scouted</span>
                <span className={s.sectionCount}>{RECENTLY_SCOUTED.length} players</span>
              </div>
              <div className={s.grid}>
                {RECENTLY_SCOUTED.map(p => <PlayerCard key={p.id} player={p} />)}
              </div>
            </div>
          )}
          <div className={s.section}>
            <div className={s.sectionHeader}>
              <span className={s.sectionTitle}>All Players</span>
              <span className={s.sectionCount}>{PLAYERS.length} players</span>
            </div>
            <div className={s.grid}>
              {PLAYERS.map(p => <PlayerCard key={p.id} player={p} />)}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
