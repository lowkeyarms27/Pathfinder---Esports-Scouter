import { RISK_STYLES, REC_STYLES } from '../lib/constants'
import s from './ValueCard.module.css'

function fmt(n) {
  if (n == null) return '—'
  return n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${n.toLocaleString()}`
}

export default function ValueCard({ result }) {
  const valueLow   = result.market_value_low
  const valueHigh  = result.market_value_high
  const risk       = result.risk_tier || 'Medium'
  const rec        = result.recommendation || 'Monitor'
  const confidence = result.value_confidence ?? 0
  const reasoning  = result.value_reasoning || ''
  const breakdown  = result.value_breakdown || {}
  const top        = breakdown.top_contributors || []
  const clips      = result.clips_analyzed ?? 1

  const riskStyle = RISK_STYLES[risk] || RISK_STYLES.Medium
  const recStyle  = REC_STYLES[rec] || REC_STYLES.Monitor
  const cardClass = rec === 'Acquire Now' ? s.cardGreen : rec === 'Monitor' ? s.cardYellow : ''

  return (
    <div className={`${s.card} ${cardClass}`}>
      <div className={s.header}>
        <div className={s.headerTitle}>Market Value</div>
        <div className={s.badges}>
          {clips > 1 && <span className={`${s.badge} ${s.badgeGreen}`}>{clips}-clip profile</span>}
          <span className={s.badge}>Illustrative</span>
        </div>
      </div>

      <div className={s.valueRow}>
        <div>
          <div className={s.valueRange}>{fmt(valueLow)} – {fmt(valueHigh)}</div>
          <div className={s.valueSub}>est. annual salary range · stylistic profile only</div>
        </div>
        <span className={s.recBadge} style={recStyle}>{rec}</span>
      </div>

      <div className={s.riskRow}>
        <span className={s.riskLabel}>Risk</span>
        <span className={s.riskBadge} style={riskStyle}>{risk}</span>
        <div className={s.confidence}>
          <span className={s.confLabel}>Confidence</span>
          <span className={s.confValue}>{Math.round(confidence * 100)}%</span>
        </div>
      </div>

      {breakdown.performance_score != null && (
        <div className={s.barWrap}>
          <div className={s.barHeader}>
            <span>Stylistic Performance</span>
            <span>{Math.round(breakdown.performance_score * 100)}%</span>
          </div>
          <div className={s.bar}>
            <div className={s.barFill} style={{ width: `${breakdown.performance_score * 100}%` }} />
          </div>
        </div>
      )}

      {top.length > 0 && (
        <>
          <hr className={s.divider} />
          <div>
            <div className={s.driversTitle}>Top Style Drivers</div>
            {top.map(([dim, val]) => (
              <div key={dim} className={s.driverRow}>
                <div className={s.driverName}>{dim.replace(/_/g, ' ')}</div>
                <div className={s.driverBar}>
                  <div className={s.driverFill} style={{ width: `${Math.min(val * 500, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {reasoning && (
        <>
          <hr className={s.divider} />
          <p className={s.reasoning}>{reasoning}</p>
        </>
      )}

      <p className={s.disclaimer}>
        Range is illustrative only — derived from stylistic profile similarity, not real transfer market data.
        {clips < 2 && ' Accuracy improves with 2–3 clips.'}
      </p>
    </div>
  )
}
