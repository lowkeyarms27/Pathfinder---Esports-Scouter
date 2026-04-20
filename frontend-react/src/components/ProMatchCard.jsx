import { ROLE_STYLES } from '../lib/constants'
import s from './ProMatchCard.module.css'

export default function ProMatchCard({ result }) {
  const match     = result.pro_match || {}
  const rawScore  = result.similarity_score ?? 0
  const dispScore = result.display_score ?? rawScore
  const rank      = result.rank ?? null
  const total     = result.total_pros ?? null
  const sims      = result.key_similarities || []
  const gaps      = result.key_gaps || []
  const alts      = result.alternatives || []
  const narrative = result.twin_narrative || ''
  const events    = match.events ?? 0

  const roleStyle = ROLE_STYLES[match.role] || { color: '#888', borderColor: '#2a2a2a', background: '#141414' }
  const arcStyle  = ROLE_STYLES[result.archetype] || { color: '#888', borderColor: '#2a2a2a', background: '#141414' }
  const scoreClass = dispScore >= 75 ? s.scoreHigh : dispScore >= 40 ? s.scoreMid : s.scoreLow

  return (
    <div className={s.card}>
      <div className={s.cardTitle}>Pro Twin Match</div>

      <div className={s.matchRow}>
        <div className={s.matchInfo}>
          <div className={s.matchHandle}>
            {match.handle || '—'}
            {match.role && (
              <span className={s.roleBadge} style={roleStyle}>{match.role}</span>
            )}
          </div>
          <div className={s.matchTeam}>{match.team || '—'}</div>
          {match.nationality && <div className={s.matchNat}>{match.nationality}</div>}
          {rank && total && (
            <div className={s.matchRank}>
              #{rank} of {total} pros
              {events > 0 && <span style={{ opacity: 0.6 }}> · {events} events</span>}
            </div>
          )}
        </div>
        <div className={s.matchScore}>
          <div className={`${s.scoreNum} ${scoreClass}`}>{dispScore}%</div>
          <div className={s.scoreLabel}>Match Score</div>
          <div className={s.scoreSub}>{rawScore}% raw cosine</div>
        </div>
      </div>

      <div className={s.bar}>
        <div className={s.barFill} style={{ width: `${dispScore}%` }} />
      </div>

      {narrative && <p className={s.narrative}>{narrative}</p>}

      {(sims.length > 0 || gaps.length > 0) && (
        <div className={s.simsGaps}>
          {sims.length > 0 && (
            <div>
              <div className={`${s.listTitle} ${s.listTitleGreen}`}>Shared Strengths</div>
              {sims.slice(0, 4).map(sim => (
                <div key={sim} className={s.listItem}>
                  <span className={s.listItemIcon}>+</span>
                  {sim.replace(/_/g, ' ')}
                </div>
              ))}
            </div>
          )}
          {gaps.length > 0 && (
            <div>
              <div className={`${s.listTitle} ${s.listTitleGray}`}>Development Gap</div>
              {gaps.slice(0, 3).map(gap => (
                <div key={gap} className={s.listItem}>
                  <span className={s.listItemIconGap}>△</span>
                  <span style={{ color: 'var(--text-muted)' }}>{gap.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {alts.length > 0 && (
        <>
          <hr className={s.divider} />
          <div>
            <div className={s.altsTitle}>Also Similar To</div>
            {alts.map(a => (
              <div key={a.handle} className={s.altRow}>
                <span className={s.altName}>
                  {a.handle} <span className={s.altTeam}>· {a.team || '—'}</span>
                  {a.rank && <span className={s.altTeam}> · #{a.rank}</span>}
                </span>
                <span className={s.altScore}>{a.display_score ?? a.similarity_score}%</span>
              </div>
            ))}
          </div>
        </>
      )}

      {result.archetype && (
        <>
          <hr className={s.divider} />
          <div className={s.archetypeRow}>
            <span className={s.archetypeLabel}>Player Archetype</span>
            <span className={s.archetypeBadge} style={arcStyle}>{result.archetype}</span>
          </div>
        </>
      )}
    </div>
  )
}
