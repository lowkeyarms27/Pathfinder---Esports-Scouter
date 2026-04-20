import s from './MatchHistoryTable.module.css'

export default function MatchHistoryTable({ matches }) {
  if (!matches?.length) return <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No match history available.</p>

  return (
    <div className={s.wrap}>
      <table className={s.table}>
        <thead>
          <tr>
            <th>Event</th>
            <th>Opponent</th>
            <th>Score</th>
            <th>Result</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {matches.map((m, i) => (
            <tr key={i}>
              <td className={s.event}>{m.event}</td>
              <td>{m.opponent}</td>
              <td className={s.score}>{m.score}</td>
              <td className={m.result === 'W' ? s.resultW : s.resultL}>{m.result}</td>
              <td className={s.date}>{m.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
