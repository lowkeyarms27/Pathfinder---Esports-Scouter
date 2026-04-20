import s from './StatCard.module.css'

export default function StatCard({ label, value, sub, accent }) {
  return (
    <div className={s.card}>
      <div className={s.label}>{label}</div>
      <div className={`${s.value} ${accent ? s.valueAccent : ''}`}>{value}</div>
      {sub && <div className={s.sub}>{sub}</div>}
    </div>
  )
}
