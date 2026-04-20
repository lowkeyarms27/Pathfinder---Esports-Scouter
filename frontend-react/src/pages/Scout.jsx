import ScoutPlayer from './ScoutPlayer'
import s from './Scout.module.css'

export default function Scout() {
  return (
    <div className={s.page}>
      <div className={s.header}>
        <div className={s.eyebrow}>AI Analysis</div>
        <div className={s.title}>Scout a Player</div>
        <div className={s.sub}>Upload a VOD or clip and get a full stylistic profile + pro comparison.</div>
      </div>
      <ScoutPlayer />
    </div>
  )
}
