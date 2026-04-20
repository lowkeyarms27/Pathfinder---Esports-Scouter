import { useParams, useNavigate } from 'react-router-dom'
import {
  RadarChart as ReRadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'
import { PLAYERS } from '../data/mockData'
import { useWatchlist } from '../context/WatchlistContext'
import StatCard from '../components/StatCard'
import MatchHistoryTable from '../components/MatchHistoryTable'
import s from './PlayerProfile.module.css'

const DIM_LABELS = {
  aggression: 'Aggression', utility_priority: 'Utility', clutch_rate: 'Clutch',
  reaction_speed: 'Reaction', flank_frequency: 'Flanking', first_duel_rate: '1st Duel',
  comms_density: 'Comms', position_variance: 'Position', trade_efficiency: 'Trades',
  site_presence: 'Site Hold', operator_diversity: 'Op Pool', info_play_rate: 'Info',
  entry_success_rate: 'Entry', utility_enable_rate: 'Utility Ena.', calm_under_pressure: 'Composure',
}

export default function PlayerProfile() {
  const { id }     = useParams()
  const navigate   = useNavigate()
  const { toggle, has } = useWatchlist()

  const player = PLAYERS.find(p => p.id === id)
  if (!player) {
    return (
      <div className={s.page}>
        <div className={s.notFound}>Player not found.</div>
      </div>
    )
  }

  const watched = has(player.id)

  const radarData = Object.entries(player.styleVector).map(([key, val]) => ({
    subject: DIM_LABELS[key] || key,
    value: Math.round(val * 100),
    fullMark: 100,
  }))

  const barData = Object.entries(player.styleVector)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([key, val]) => ({ name: DIM_LABELS[key] || key, value: Math.round(val * 100) }))

  return (
    <div className={s.page}>
      <button className={s.back} onClick={() => navigate(-1)}>
        ← Back
      </button>

      <div className={s.hero}>
        <div className={s.avatar}>{player.handle.slice(0, 2).toUpperCase()}</div>
        <div className={s.heroInfo}>
          <div className={s.handle}>{player.handle}</div>
          <div className={s.realName}>{player.nationality} {player.realName} · {player.team} · Age {player.age}</div>
          <div className={s.tags}>
            <span className={`${s.tag} ${s.tagRole}`}>{player.role}</span>
            <span className={`${s.tag} ${s.tagGame}`}>{player.game}</span>
            <span className={s.tag}>{player.events} events</span>
          </div>
        </div>
        <div className={s.heroRight}>
          <div className={s.score}>
            <div className={s.scoreNum}>{player.matchScore}</div>
            <div className={s.scoreLabel}>Pro Match Score</div>
          </div>
          <button
            className={`${s.watchBtn} ${watched ? s.watchBtnActive : ''}`}
            onClick={() => toggle(player)}
          >
            {watched ? '★ Watching' : '+ Add to Watchlist'}
          </button>
        </div>
      </div>

      <div className={s.statsGrid}>
        <StatCard label="Match Score" value={player.matchScore} accent />
        <StatCard label="Market Value" value={player.marketValue.label} sub="Illustrative range" />
        <StatCard label="Events Tracked" value={player.events} sub="Tournament matches" />
        <StatCard label="Role" value={player.role} />
        <StatCard label="Nationality" value={player.nationality} />
        <StatCard label="Age" value={player.age} />
      </div>

      <div className={s.twoCol}>
        <div className={s.card}>
          <div className={s.cardTitle}>Stylistic DNA — Radar</div>
          <ResponsiveContainer width="100%" height={240}>
            <ReRadarChart data={radarData}>
              <PolarGrid stroke="rgba(255,255,255,0.06)" />
              <PolarAngleAxis
                dataKey="subject"
                tick={{ fill: '#555', fontSize: 9, fontFamily: 'inherit' }}
              />
              <Radar
                name={player.handle}
                dataKey="value"
                stroke="#00ff88"
                fill="#00ff88"
                fillOpacity={0.12}
                strokeWidth={2}
              />
            </ReRadarChart>
          </ResponsiveContainer>
        </div>

        <div className={s.card}>
          <div className={s.cardTitle}>Top Attributes</div>
          <div className={s.chartContainer}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} layout="vertical" margin={{ left: 8, right: 24 }}>
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#555', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" width={80} tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#141414', border: '1px solid #2a2a2a', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#f0f0f0' }}
                  itemStyle={{ color: '#00ff88' }}
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {barData.map((entry, i) => (
                    <Cell key={i} fill={i === 0 ? '#00ff88' : `rgba(0,255,136,${0.6 - i * 0.06})`} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className={s.twoCol}>
        <div className={s.card}>
          <div className={s.cardTitle}>Bio</div>
          <p className={s.bio}>{player.bio}</p>
        </div>
        <div className={s.card}>
          <div className={s.cardTitle}>Analyst Traits</div>
          <div className={s.traits}>
            {player.traits.map((t, i) => (
              <div key={i} className={s.trait}>
                <span className={s.traitIcon}>▲</span>
                {t}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={s.card}>
        <div className={s.cardTitle}>Match History</div>
        <MatchHistoryTable matches={player.matchHistory} />
      </div>
    </div>
  )
}
