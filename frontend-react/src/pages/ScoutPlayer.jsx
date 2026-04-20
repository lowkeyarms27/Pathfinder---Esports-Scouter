import { useState, useEffect, useRef } from 'react'
import { submitScout, submitScoutMulti, getStatus, getLog, getResults } from '../lib/api'
import Pipeline, { currentStep } from '../components/Pipeline'
import RadarChart from '../components/RadarChart'
import ProMatchCard from '../components/ProMatchCard'
import ValueCard from '../components/ValueCard'
import { ROLE_STYLES } from '../lib/constants'
import s from './ScoutPlayer.module.css'

const POLL_MS = 2500

export default function ScoutPlayer() {
  const [files,     setFiles]     = useState([null, null, null])
  const [multiMode, setMultiMode] = useState(false)
  const [handle,    setHandle]    = useState('')
  const [team,      setTeam]      = useState('')
  const [game,      setGame]      = useState('r6siege')
  const [sessionId, setSessionId] = useState(null)
  const [status,    setStatus]    = useState(null)
  const [log,       setLog]       = useState([])
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState(null)
  const [uploading, setUploading] = useState(false)
  const pollRef  = useRef(null)
  const fileRefs = [useRef(null), useRef(null), useRef(null)]

  const activeFiles = multiMode ? files.filter(Boolean) : (files[0] ? [files[0]] : [])
  const canSubmit   = activeFiles.length >= (multiMode ? 2 : 1) && handle.trim()

  useEffect(() => () => clearInterval(pollRef.current), [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    setError(null); setResult(null); setLog([]); setStatus(null); setUploading(true)
    try {
      const fd = new FormData()
      fd.append('player_handle', handle.trim())
      fd.append('game', game)
      fd.append('team', team.trim())
      let session_id
      if (multiMode && activeFiles.length >= 2) {
        activeFiles.forEach(f => fd.append('clips', f))
        ;({ session_id } = await submitScoutMulti(fd))
      } else {
        fd.append('clip', activeFiles[0])
        ;({ session_id } = await submitScout(fd))
      }
      setSessionId(session_id)
      setStatus('uploading')
      setUploading(false)
      pollRef.current = setInterval(() => poll(session_id), POLL_MS)
    } catch (err) {
      setError(err.message)
      setUploading(false)
    }
  }

  async function poll(sid) {
    try {
      const [st, l] = await Promise.all([getStatus(sid), getLog(sid)])
      setStatus(st.status)
      setLog(l.log || [])
      if (st.status === 'complete') {
        clearInterval(pollRef.current)
        const r = await getResults(sid)
        setResult(r.full_result || r)
      } else if (st.status === 'failed') {
        clearInterval(pollRef.current)
        setError(st.error || 'Analysis failed')
      }
    } catch (err) {
      setError(err.message)
      clearInterval(pollRef.current)
    }
  }

  const running  = status && !['complete', 'failed'].includes(status)
  const step     = currentStep(log)
  const arcStyle = result ? (ROLE_STYLES[result.archetype] || {}) : {}

  const sensorClass = result
    ? result.sensors_active >= 7 ? s.sensorGood
    : result.sensors_active >= 5 ? s.sensorMid
    : s.sensorLow
    : ''

  return (
    <div className={s.wrap}>
      {/* Upload form */}
      <div className={s.uploadCard}>
        <div className={s.cardTitle}>Scout a Player</div>
        <form onSubmit={handleSubmit}>
          <div className={s.fieldGrid}>
            <div>
              <label className={s.fieldLabel}>Player Handle *</label>
              <input
                className={s.input}
                type="text"
                value={handle}
                onChange={e => setHandle(e.target.value)}
                placeholder="e.g. xXxPlayer123"
                required
              />
            </div>
            <div>
              <label className={s.fieldLabel}>Team (optional)</label>
              <input
                className={s.input}
                type="text"
                value={team}
                onChange={e => setTeam(e.target.value)}
                placeholder="e.g. Team Liquid Academy"
              />
            </div>
            <div>
              <label className={s.fieldLabel}>Game</label>
              <select className={s.select} value={game} onChange={e => setGame(e.target.value)}>
                <option value="r6siege">Rainbow Six Siege</option>
              </select>
            </div>
          </div>

          <div className={s.modeRow}>
            <button type="button" className={`${s.modeBtn} ${!multiMode ? s.modeBtnActive : ''}`} onClick={() => setMultiMode(false)}>
              Single Clip
            </button>
            <button type="button" className={`${s.modeBtn} ${multiMode ? s.modeBtnActive : ''}`} onClick={() => setMultiMode(true)}>
              Multi-clip (2–3)
            </button>
            {multiMode && <span className={s.modeHint}>Averages style vectors for better accuracy</span>}
          </div>

          <div className={`${s.dropGrid} ${multiMode ? s.dropGrid3 : s.dropGrid1}`}>
            {(multiMode ? [0, 1, 2] : [0]).map(i => (
              <div
                key={i}
                className={`${s.dropZone} ${files[i] ? s.dropZoneActive : ''}`}
                onClick={() => fileRefs[i].current?.click()}
              >
                <input
                  ref={fileRefs[i]}
                  type="file"
                  accept="video/*"
                  style={{ display: 'none' }}
                  onChange={e => {
                    const next = [...files]
                    next[i] = e.target.files[0] || null
                    setFiles(next)
                  }}
                />
                {files[i] ? (
                  <>
                    <div className={s.dropFileName}>{files[i].name}</div>
                    <div className={s.dropFileSize}>{(files[i].size / 1024 / 1024).toFixed(1)} MB</div>
                  </>
                ) : (
                  <>
                    <div className={s.dropIcon}>▲</div>
                    <div className={s.dropLabel}>
                      {multiMode ? `Clip ${i + 1}${i >= 2 ? ' (optional)' : ''}` : 'Drop a VOD or clip here'}
                    </div>
                    {!multiMode && <div className={s.dropHint}>MP4, MOV, AVI — up to 2 GB</div>}
                  </>
                )}
              </div>
            ))}
          </div>

          <button type="submit" className={s.submitBtn} disabled={!canSubmit || uploading || running}>
            {uploading ? 'Uploading…' : running ? 'Analysing…' : multiMode ? `Scout Player (${activeFiles.length} clips)` : 'Scout Player'}
          </button>
        </form>

        {error && <div className={s.error}>{error}</div>}
      </div>

      {/* Pipeline */}
      {(running || (status === 'complete' && log.length > 0)) && (
        <Pipeline step={step} log={log} sensorStatus={result?.sensor_status} />
      )}

      {/* Results */}
      {result && (
        <div className={s.resultsWrap}>
          {/* Header */}
          <div className={s.resultHeader}>
            <div className={s.resultHeaderRow}>
              <div>
                <div className={s.resultHandle}>{result.player_handle}</div>
                <div className={s.resultBadges}>
                  {result.archetype && (
                    <span className={s.badge} style={arcStyle}>{result.archetype}</span>
                  )}
                  {result.clips_analyzed > 1 && (
                    <span className={`${s.badge} ${s.badgeClips}`}>{result.clips_analyzed}-clip profile</span>
                  )}
                </div>
              </div>
              <div className={s.resultScoreBlock}>
                {result.similarity_score != null && (
                  <>
                    <div className={s.resultScore}>{result.display_score ?? result.similarity_score}%</div>
                    <div className={s.resultScoreLabel}>Pro Match</div>
                  </>
                )}
                {result.sensors_total > 0 && (
                  <span className={`${s.sensorBadge} ${sensorClass}`}>
                    {result.sensors_active}/{result.sensors_total} sensors
                  </span>
                )}
              </div>
            </div>

            {result.traits?.length > 0 && (
              <div className={s.traits}>
                {result.traits.map((t, i) => (
                  <div key={i} className={s.trait}>
                    <span className={s.traitIcon}>▲</span>
                    {t}
                  </div>
                ))}
              </div>
            )}

            {result.raw_analysis && (
              <p className={s.rawAnalysis}>{result.raw_analysis}</p>
            )}
          </div>

          {/* Radar + pro match */}
          <div className={s.twoCol}>
            <div className={s.card}>
              <div className={s.cardTitle}>Stylistic DNA</div>
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <RadarChart vector={result.style_vector || {}} size={260} />
              </div>
              <div className={s.radarLegend}>
                <div className={s.legendItem}>
                  <span className={s.legendLine} />
                  This player
                </div>
              </div>
            </div>
            <ProMatchCard result={result} />
          </div>

          {result.market_value != null && <ValueCard result={result} />}

          {result.highlight_clips?.length > 0 && (
            <div className={s.card}>
              <div className={s.cardTitle}>Highlight Clips ({result.highlight_clips.length})</div>
              <div className={s.clipsGrid}>
                {result.highlight_clips.map((clip, i) => (
                  <div key={i}>
                    <div className={s.clipLabel}>Highlight {i + 1}</div>
                    <video src={clip} controls className={s.clipVideo} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
