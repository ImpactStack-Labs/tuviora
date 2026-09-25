export default function StatCard({
  label,
  value,
  icon: Icon,
  caption,
  accent = 'bg-[#EDF3E8] text-[#58761B]',
}) {
  return (
    <div className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-text-muted">{label}</p>
        <span className={`shrink-0 rounded-xl p-2.5 ${accent}`}>
          <Icon size={20} />
        </span>
      </div>
      <p className="mt-4 text-3xl font-bold tracking-tight text-[#1A3F22]">
        {value}
      </p>
      {caption && (
        <p className="mt-2 text-sm text-text-muted">{caption}</p>
      )}
    </div>
  )
}
