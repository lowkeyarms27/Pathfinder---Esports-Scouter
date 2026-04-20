export default function Topbar({ tab, tabs, onTab }) {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-sm">
      <div className="max-w-screen-xl mx-auto px-8 flex items-center gap-8 h-14">
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-slate-950 text-xs font-black shadow-[0_0_16px_rgba(52,211,153,0.35)]">
            ▲
          </div>
          <div>
            <div className="text-sm font-bold text-slate-50 leading-none tracking-tight">Pathfinder</div>
            <div className="text-[9px] text-slate-700 uppercase tracking-[2px] font-semibold leading-none mt-0.5">
              Esports Scout
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-1">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => onTab(t.id)}
              className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all ${
                tab === t.id
                  ? 'bg-emerald-400 text-slate-950'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="text-[9px] font-bold uppercase tracking-widest text-emerald-400/60 border border-emerald-400/15 bg-emerald-400/5 px-2.5 py-1 rounded-full">
            ▲ Gemini 2.5 Flash
          </span>
          <span className="text-[9px] font-bold uppercase tracking-widest text-slate-600 border border-slate-800 bg-slate-900 px-2.5 py-1 rounded-full">
            9 ML Sensors
          </span>
          <span className="text-[9px] font-bold uppercase tracking-widest text-slate-600 border border-slate-800 bg-slate-900 px-2.5 py-1 rounded-full">
            Scouting by Reward
          </span>
        </div>
      </div>
    </header>
  )
}
