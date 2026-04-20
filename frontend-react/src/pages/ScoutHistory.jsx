import { useState, useEffect } from 'react'
import { getSessions, getResults } from '../lib/api'
import RadarChart from '../components/RadarChart'
import { ROLE_COLORS, RISK_COLORS, REC_COLORS } from '../lib/constants'

export default function ScoutHistory() {
  const [sessions,  setSessions]  = useState([])
  const [selected,  setSelected]  = useState(null)
  const [result,    setResult]    = useState(null)
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    getSessions().then(d => {
      setSessions(d.sessions || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  async function openSession(s) {
    setSelected(s)
    setResult(null)
    if (s.status === 'complete') {
      const d = await getResults(s.id)
      setResult(d?.full_result || d || null)
    }
  }

  const recCls = (rec) => REC_COLORS[rec] || REC_COLORS.Monitor

  return (
    <div className="space-y-6">
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Scouting History</div>

      {loading && <div className="text-sm text-slate-600">Loading…</div>}
      {!loading && sessions.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center text-slate-600 text-sm">
          No sessions yet. Scout your first player to get started.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Session list */}
        <div className="lg:col-span-1 space-y-2">
          {sessions.map(s => {
            const arcColor = ROLE_COLORS[s.archetype] || 'text-slate-500'
            const isActive = selected?.id === s.id
            return (
              <button
                key={s.id}
                onClick={() => openSession(s)}
                className={`w-full text-left rounded-xl border px-4 py-3 transition-all ${
                  isActive
                    ? 'border-emerald-500/40 bg-emerald-500/5'
                    : 'border-slate-800 bg-slate-900 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-slate-200 truncate">
                      {s.player_handle || 'Unknown'}
                    </div>
                    {s.archetype && (
                      <div className={`text-[10px] font-semibold mt-0.5 ${arcColor.split(' ')[0]}`}>
                        {s.archetype}
                      </div>
                    )}
                    <div className="text-xs text-slate-600 mt-0.5">
                      {s.game} · {new Date(s.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    {s.similarity_score != null && (
                      <div className="text-sm font-black text-emerald-400">{s.similarity_score}%</div>
                    )}
                    {s.market_value != null && (
                      <div className="text-[10px] text-slate-500">${s.market_value.toLocaleString()}</div>
                    )}
                    <div className={`text-[9px] mt-1 px-1.5 py-0.5 rounded border font-bold uppercase tracking-wider ${
                      s.status === 'complete' ? 'text-emerald-600 border-emerald-800 bg-emerald-900/20'
                      : s.status === 'failed' ? 'text-red-600 border-red-900 bg-red-900/20'
                      : 'text-yellow-600 border-yellow-900 bg-yellow-900/20'
                    }`}>
                      {s.status}
                    </div>
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {/* Detail panel */}
        <div className="lg:col-span-2">
          {!selected && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center text-slate-600 text-sm h-full flex items-center justify-center">
              Select a session to view the scouting report
            </div>
          )}

          {selected && !result && selected.status === 'complete' && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center text-slate-600 text-sm">
              Loading…
            </div>
          )}

          {selected && selected.status !== 'complete' && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-sm text-slate-500">
              Status: <span className="text-yellow-400 font-semibold">{selected.status}</span>
              {selected.error_message && (
                <div className="mt-2 text-red-400">{selected.error_message}</div>
              )}
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Header */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    <div className="text-xl font-black text-slate-50">{result.player_handle}</div>
                    {result.archetype && (
                      <span className={`inline-block mt-1 text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${ROLE_COLORS[result.archetype] || 'text-slate-400 border-slate-700 bg-slate-800'}`}>
                        {result.archetype}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    {result.recommendation && (
                      <span className={`text-xs font-bold uppercase tracking-wider px-3 py-1.5 rounded-full border ${recCls(result.recommendation)}`}>
                        {result.recommendation}
                      </span>
                    )}
                    {result.market_value != null && (
                      <div className="text-right">
                        <div className="text-xl font-black text-slate-50">${result.market_value.toLocaleString()}</div>
                        <div className="text-[9px] text-slate-600 uppercase tracking-widest">/year est.</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Pro match summary */}
                {result.pro_match && (
                  <div className="mt-4 pt-4 border-t border-slate-800 flex items-center gap-3">
                    <span className="text-xs text-slate-500">Plays like</span>
                    <span className="text-sm font-bold text-slate-200">{result.pro_match.handle}</span>
                    <span className="text-xs text-slate-600">{result.pro_match.team}</span>
                    <span className="text-emerald-400 font-black text-sm ml-auto">{result.similarity_score}%</span>
                  </div>
                )}
              </div>

              {/* Radar */}
              {result.style_vector && (
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600 mb-3">Stylistic DNA</div>
                  <div className="flex justify-center">
                    <RadarChart vector={result.style_vector} size={240} />
                  </div>
                </div>
              )}

              {/* Traits */}
              {result.traits?.length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-1.5">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600 mb-2">Scout Notes</div>
                  {result.traits.map((t, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-slate-400">
                      <span className="text-emerald-500 mt-0.5 shrink-0">▲</span>
                      {t}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
