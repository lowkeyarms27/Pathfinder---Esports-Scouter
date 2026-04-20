import { PIPELINE_STEPS, AGENT_TO_STEP, SENSOR_LABELS } from '../lib/constants'
import s from './Pipeline.module.css'

export function currentStep(log) {
  for (let i = (log || []).length - 1; i >= 0; i--) {
    const e = log[i]
    if (e.action === 'complete' && e.agent in AGENT_TO_STEP) {
      return AGENT_TO_STEP[e.agent] + 1
    }
  }
  return 0
}

function SensorGrid({ sensorStatus }) {
  if (!sensorStatus || Object.keys(sensorStatus).length === 0) return null
  return (
    <div className={s.sensorGrid}>
      <div className={s.sensorGridTitle}>ML Sensor Coverage</div>
      <div className={s.sensorList}>
        {Object.entries(sensorStatus).map(([key, active]) => (
          <div key={key} className={s.sensorItem}>
            <span className={`${s.sensorDot} ${active ? s.sensorDotOn : s.sensorDotOff}`} />
            <span className={`${s.sensorName} ${active ? s.sensorNameOn : s.sensorNameOff}`}>
              {SENSOR_LABELS[key] || key}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Pipeline({ step, log, sensorStatus }) {
  const recent = (log || []).filter(e => e.action === 'complete').slice(-3)
  const desc = PIPELINE_STEPS[Math.min(step, PIPELINE_STEPS.length - 1)]?.desc || ''

  const observerLog  = (log || []).find(e => e.agent === 'observer' && e.action === 'complete')
  const sensorMatch  = observerLog?.detail?.match(/(\d+)\/(\d+) sensors active/)
  const sensorsActive = sensorMatch ? parseInt(sensorMatch[1]) : null
  const sensorsTotal  = sensorMatch ? parseInt(sensorMatch[2]) : null

  const sensorClass = sensorsActive === null ? ''
    : sensorsActive >= 7 ? s.sensorGood
    : sensorsActive >= 5 ? s.sensorMid
    : s.sensorLow

  return (
    <div className={s.wrap}>
      <div className={s.header}>
        <div className={s.title}>Pipeline</div>
        {sensorsActive !== null && (
          <span className={`${s.sensorBadge} ${sensorClass}`}>
            {sensorsActive}/{sensorsTotal} sensors
          </span>
        )}
      </div>

      <div className={s.steps}>
        {PIPELINE_STEPS.map((ps, i) => {
          const done   = i < step
          const active = i === step
          return (
            <div key={i} className={s.step}>
              {i < PIPELINE_STEPS.length - 1 && (
                <div className={`${s.connector} ${done ? s.connectorDone : s.connectorPending}`} />
              )}
              <div className={`${s.dot} ${done ? s.dotDone : active ? s.dotActive : s.dotPending}`}>
                {done ? '✓' : i + 1}
              </div>
              <div className={`${s.stepLabel} ${done ? s.labelDone : active ? s.labelActive : s.labelPending}`}>
                {ps.label}
              </div>
            </div>
          )
        })}
      </div>

      <div className={s.desc}>{desc}…</div>

      {recent.length > 0 && (
        <div className={s.log}>
          {recent.map((e, i) => (
            <div key={i} className={s.logRow}>
              <span className={s.logAgent}>{e.agent}</span>
              <span className={s.logDetail}>{(e.detail || '').slice(0, 80)}</span>
            </div>
          ))}
        </div>
      )}

      {sensorStatus && <SensorGrid sensorStatus={sensorStatus} />}
    </div>
  )
}
