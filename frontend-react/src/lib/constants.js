export const PIPELINE_STEPS = [
  { label: 'Observe',  desc: 'Running 9 ML sensors on VOD' },
  { label: 'Profile',  desc: 'Building Stylistic DNA' },
  { label: 'Twin',     desc: 'Finding pro match' },
  { label: 'Value',    desc: 'Estimating market value' },
]

export const AGENT_TO_STEP = {
  observer:     0,
  profiler:     1,
  twin:         2,
  value_critic: 3,
}

export const ROLE_STYLES = {
  'Entry Fragger': { color: '#ff6666', borderColor: 'rgba(255,102,102,0.3)', background: 'rgba(255,102,102,0.1)' },
  'Anchor':        { color: '#4488ff', borderColor: 'rgba(68,136,255,0.3)',   background: 'rgba(68,136,255,0.1)' },
  'Roamer':        { color: '#ffcc00', borderColor: 'rgba(255,204,0,0.3)',    background: 'rgba(255,204,0,0.1)' },
  'Hard Breach':   { color: '#ff8844', borderColor: 'rgba(255,136,68,0.3)',   background: 'rgba(255,136,68,0.1)' },
  'Support':       { color: '#00ff88', borderColor: 'rgba(0,255,136,0.3)',    background: 'rgba(0,255,136,0.1)' },
  'IGL':           { color: '#aa44ff', borderColor: 'rgba(170,68,255,0.3)',   background: 'rgba(170,68,255,0.1)' },
  'Flex':          { color: '#44ccff', borderColor: 'rgba(68,204,255,0.3)',   background: 'rgba(68,204,255,0.1)' },
}

export const RISK_STYLES = {
  Low:    { color: '#00ff88', borderColor: 'rgba(0,255,136,0.3)',    background: 'rgba(0,255,136,0.1)' },
  Medium: { color: '#ffcc00', borderColor: 'rgba(255,204,0,0.3)',    background: 'rgba(255,204,0,0.1)' },
  High:   { color: '#ff4444', borderColor: 'rgba(255,68,68,0.3)',    background: 'rgba(255,68,68,0.1)' },
}

export const REC_STYLES = {
  'Acquire Now': { color: '#00ff88', borderColor: 'rgba(0,255,136,0.3)',    background: 'rgba(0,255,136,0.1)' },
  'Monitor':     { color: '#ffcc00', borderColor: 'rgba(255,204,0,0.3)',    background: 'rgba(255,204,0,0.1)' },
  'Pass':        { color: '#666',    borderColor: '#2a2a2a',                background: '#141414' },
}

// kept for any legacy references
export const ROLE_COLORS  = ROLE_STYLES
export const RISK_COLORS  = RISK_STYLES
export const REC_COLORS   = REC_STYLES

// All 15 style dimensions for radar chart
export const RADAR_DIMS = [
  { key: 'aggression',          label: 'Aggression' },
  { key: 'reaction_speed',      label: 'Reaction' },
  { key: 'entry_success_rate',  label: 'Entry Win %' },
  { key: 'clutch_rate',         label: 'Clutch' },
  { key: 'first_duel_rate',     label: 'First Duel' },
  { key: 'trade_efficiency',    label: 'Trade Eff.' },
  { key: 'utility_priority',    label: 'Util Priority' },
  { key: 'utility_enable_rate', label: 'Util Enable' },
  { key: 'site_presence',       label: 'Site Pres.' },
  { key: 'info_play_rate',      label: 'Info Play' },
  { key: 'calm_under_pressure', label: 'Composure' },
  { key: 'comms_density',       label: 'Comms' },
  { key: 'flank_frequency',     label: 'Flank Freq.' },
  { key: 'position_variance',   label: 'Positioning' },
  { key: 'operator_diversity',  label: 'Op. Pool' },
]

export const SENSOR_LABELS = {
  gemini:  'Gemini Vision',
  pegasus: 'Twelve Labs',
  yolo:    'YOLO Detection',
  whisper: 'Whisper Audio',
  ocr:     'HUD OCR',
  tracker: 'Player Tracker',
  audio:   'Audio Events',
  clip:    'CLIP Concepts',
  spatial: 'Spatial AI',
}
